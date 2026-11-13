# Quick Poll

Quick Poll is a small voting app for the DevOps and CI/CD Pipelines final project. Users create a poll, vote, and watch the results update live.

## Run it on your computer

```bash
python -m venv .venv
source .venv/Scripts/activate      # on a Mac: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:8080 in your browser.

## Run the linter and the tests

```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

## Pages

| Page | What it shows |
| --- | --- |
| `/` | All polls |
| `/polls/new` | A form to create a poll |
| `/polls/<id>` | A poll with voting buttons and live results |
| `/api/polls/<id>` | The results of a poll as JSON |
| `/health` | The status, version, and environment as JSON |
| `/metrics` | Metrics for Prometheus, such as `votes_total` and `http_requests_total` |

## Settings

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `APP_PORT` | `8080` | The port the app listens on |
| `APP_ENV` | `local` | The environment name shown on every page, such as dev or prod |
| `DATA_DIR` | `data` | The folder that keeps the database file `polls.db` |
| `APP_TITLE` | `Quick Poll` | The name shown at the top of every page |
