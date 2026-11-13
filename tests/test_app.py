"""test_app.py: unit tests for Quick Poll. Run them with: pytest"""
import pytest

import app as quickpoll


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(quickpoll, "DATA_DIR", str(tmp_path))  # a fresh database for each test
    quickpoll.app.config["TESTING"] = True
    return quickpoll.app.test_client()


def test_health(client):
    data = client.get("/health").get_json()
    assert data["status"] == "ok"
    assert data["version"] == quickpoll.VERSION


def test_home_shows_sample_poll(client):
    page = client.get("/").get_data(as_text=True)
    assert "Which DevOps tool do you enjoy the most?" in page


def test_create_poll(client):
    response = client.post("/polls/new", data={"question": "Tea or coffee?", "option": ["Tea", "Coffee"]})
    assert response.status_code == 302
    assert "Tea or coffee?" in client.get(response.headers["Location"]).get_data(as_text=True)


def test_poll_needs_two_options(client):
    response = client.post("/polls/new", data={"question": "Only one?", "option": ["Yes"]})
    assert response.status_code == 400


def test_vote_is_counted(client):
    option_id = client.get("/api/polls/1").get_json()["options"][0]["id"]
    client.post("/polls/1/vote", data={"option": option_id})
    poll = client.get("/api/polls/1").get_json()
    assert poll["total"] == 1
    assert poll["options"][0]["percent"] == 100


def test_unknown_poll_returns_404(client):
    assert client.get("/polls/999").status_code == 404


def test_metrics_page(client):
    assert "votes_total" in client.get("/metrics").get_data(as_text=True)
