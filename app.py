"""app.py: Quick Poll 1.0.0, a small voting app for the DevOps final project."""
import os  # reads environment variables and builds file paths
import socket  # finds the name of the container that answers
import sqlite3  # stores polls and votes in a small database file
import time  # measures how long each request takes

from flask import Flask, abort, g, jsonify, redirect, render_template, request, url_for
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

VERSION = "1.0.0"
PORT = int(os.environ.get("APP_PORT", "8080"))  # port to listen on
APP_ENV = os.environ.get("APP_ENV", "local")  # where this copy runs: local, dev, or prod
DATA_DIR = os.environ.get("DATA_DIR", "data")  # folder that keeps the database file
APP_TITLE = os.environ.get("APP_TITLE", "Quick Poll")  # name shown at the top of each page

# Metrics that Prometheus reads from the /metrics page
REQUESTS = Counter("http_requests", "Total HTTP requests.", ["path", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Request time.", ["path"])
VOTES = Counter("votes", "Total votes cast.")
POLLS = Gauge("polls_total", "Number of polls.")

app = Flask(__name__)


def db_path():
    return os.path.join(DATA_DIR, "polls.db")


def get_db():  # opens one database connection per request
    if "db" not in g:
        os.makedirs(DATA_DIR, exist_ok=True)
        g.db = sqlite3.connect(db_path())
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():  # creates the tables, and a sample poll the first time
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS polls (id INTEGER PRIMARY KEY, question TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS options (
            id INTEGER PRIMARY KEY, poll_id INTEGER NOT NULL,
            label TEXT NOT NULL, votes INTEGER NOT NULL DEFAULT 0);
    """)
    if db.execute("SELECT COUNT(*) FROM polls").fetchone()[0] == 0:
        create_poll("Which DevOps tool do you enjoy the most?",
                    ["GitHub Actions", "Docker", "Kubernetes", "Terraform"])
    db.commit()
    POLLS.set(db.execute("SELECT COUNT(*) FROM polls").fetchone()[0])


def create_poll(question, labels):  # saves a poll with its options, returns its id
    db = get_db()
    poll_id = db.execute("INSERT INTO polls (question) VALUES (?)", (question,)).lastrowid
    db.executemany("INSERT INTO options (poll_id, label) VALUES (?, ?)",
                   [(poll_id, label) for label in labels])
    db.commit()
    POLLS.set(db.execute("SELECT COUNT(*) FROM polls").fetchone()[0])
    return poll_id


def get_poll(poll_id):  # returns a poll with its options and totals, or None
    db = get_db()
    poll = db.execute("SELECT * FROM polls WHERE id = ?", (poll_id,)).fetchone()
    if poll is None:
        return None
    options = [dict(o) for o in db.execute(
        "SELECT id, label, votes FROM options WHERE poll_id = ? ORDER BY id", (poll_id,))]
    total = sum(o["votes"] for o in options)
    for o in options:
        o["percent"] = round(100 * o["votes"] / total) if total else 0
    return {"id": poll["id"], "question": poll["question"], "options": options, "total": total}


@app.before_request
def start_timer():
    g.start = time.perf_counter()
    init_db()


@app.after_request
def record_metrics(response):  # counts every request and how long it took
    rule = request.url_rule.rule if request.url_rule else "other"
    REQUESTS.labels(rule, str(response.status_code)).inc()
    LATENCY.labels(rule).observe(time.perf_counter() - g.get("start", time.perf_counter()))
    return response


@app.context_processor
def page_info():  # values every page shows in the header and footer
    return {"app_title": APP_TITLE, "version": VERSION, "app_env": APP_ENV,
            "host": socket.gethostname()}


@app.route("/")
def index():
    ids = [r["id"] for r in get_db().execute("SELECT id FROM polls ORDER BY id DESC")]
    return render_template("index.html", polls=[get_poll(i) for i in ids])


@app.route("/polls/new", methods=["GET", "POST"])
def new_poll():
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        labels = [x.strip() for x in request.form.getlist("option") if x.strip()]
        if not question or len(labels) < 2:
            return render_template("new.html", error="Enter a question and at least two options.",
                                   question=question, labels=labels), 400
        return redirect(url_for("show_poll", poll_id=create_poll(question, labels[:6])))
    return render_template("new.html", error=None, question="", labels=[])


@app.route("/polls/<int:poll_id>")
def show_poll(poll_id):
    poll = get_poll(poll_id)
    if poll is None:
        abort(404)
    return render_template("poll.html", poll=poll)


@app.route("/polls/<int:poll_id>/vote", methods=["POST"])
def vote(poll_id):
    db = get_db()
    option_id = request.form.get("option", type=int)
    updated = db.execute("UPDATE options SET votes = votes + 1 WHERE id = ? AND poll_id = ?",
                         (option_id, poll_id)).rowcount
    if not updated:
        abort(400)
    db.commit()
    VOTES.inc()
    return redirect(url_for("show_poll", poll_id=poll_id, voted=1))


@app.route("/api/polls/<int:poll_id>")
def poll_json(poll_id):  # the live results that the poll page reads every few seconds
    poll = get_poll(poll_id)
    if poll is None:
        abort(404)
    return jsonify(poll)


@app.route("/health")
def health():
    return jsonify(status="ok", version=VERSION, environment=APP_ENV)


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    print(f"{APP_TITLE} {VERSION} ({APP_ENV}) on port {PORT}", flush=True)
    app.run(host="0.0.0.0", port=PORT)
