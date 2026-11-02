# Uptime Monitor

A portfolio project for monitoring API availability and response time.

## Planned stack

- Python 3.14 and FastAPI
- PostgreSQL
- Docker
- GitHub Actions

## Project status

Current milestone: FastAPI health endpoints, PostgreSQL models and migration, JWT signup/login, owner-scoped monitor management, and a bounded asynchronous check runner.

## Architecture

```mermaid
flowchart LR
    User --> API[FastAPI]
    API --> DB[(PostgreSQL)]
    Scheduler[GitHub Actions] -->|protected trigger| API
    API --> CheckService[Async check service]
    CheckService --> MonitoredAPI[Monitored APIs]
```

## API endpoints

- `POST /auth/register` — create an account
- `POST /auth/login` — receive a short-lived bearer token
- `GET /auth/me` — view the authenticated account
- `POST /monitors` — create a monitor (authentication required)
- `GET /monitors` — list your monitors (authentication required)
- `GET /monitors/{id}` — view a monitor (authentication required)
- `PATCH /monitors/{id}` — update a monitor (authentication required)
- `DELETE /monitors/{id}` — delete a monitor (authentication required)
- `GET /monitors/{id}/results` — view recent check history (authentication required)
- `POST /internal/run-due-checks` — run due checks (scheduler bearer token required)
- `GET /health` — API process health
- `GET /health/database` — PostgreSQL connectivity

## Free-tier deployment note

This is a portfolio demo. Free hosting may sleep when idle, and scheduled jobs may be delayed. It does not provide a production uptime guarantee.

## Local development

1. Copy `.env.example` to `.env` and set `DATABASE_URL` to your PostgreSQL connection string.
2. Install dependencies: `python -m pip install -r requirements.txt`.
3. Apply the database schema: `alembic upgrade head`.
4. Start the API: `python -m uvicorn app.main:app`.

The `.env` file contains secrets and must never be committed.
