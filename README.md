# Pose_API

FastAPI REST API — autenticación JWT, reportes Excel y ETL trigger para el ecosistema POSE

## Overview

**Pose_API** is a production-ready REST API for the POSE (Posture & Open Sport Engine) ecosystem. It provides:

- 🔐 **JWT Authentication** — register, login, token refresh, logout, and protected routes
- 📊 **Excel Report Generation** — download pose-session data as richly-formatted `.xlsx` files
- ⚙️ **ETL Pipeline Triggers** — securely kick off data-pipeline jobs in the POSE data warehouse

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | [FastAPI](https://fastapi.tiangolo.com/) 0.111 |
| Authentication | JWT (`python-jose`) + bcrypt |
| ORM | SQLAlchemy 2.0 + SQLite (dev) / any SQL DB (prod) |
| Excel | openpyxl 3.1 |
| Data processing | pandas 2.2 |
| Tests | pytest + `TestClient` |

---

## Project Structure

```
Pose_API/
├── app/
│   ├── main.py            # FastAPI app, middleware, router registration
│   ├── config.py          # Pydantic Settings (reads .env)
│   ├── database.py        # SQLAlchemy engine & session factory
│   ├── models.py          # POSE domain models (PoseSession, PoseKeypoint)
│   ├── auth/
│   │   ├── models.py      # User & RefreshToken ORM models
│   │   ├── schemas.py     # Pydantic request/response schemas
│   │   ├── utils.py       # Password hashing, JWT creation/decoding
│   │   └── router.py      # /auth/* endpoints + current-user dependency
│   ├── reports/
│   │   ├── excel.py       # Excel workbook builder
│   │   └── router.py      # /reports/* endpoints
│   └── etl/
│       ├── schemas.py     # ETL request/response schemas
│       ├── service.py     # HTTP client for the ETL service
│       └── router.py      # /etl/* endpoints
├── tests/
│   ├── conftest.py        # pytest fixtures (in-memory DB, test client)
│   ├── test_auth.py       # Auth endpoint tests
│   ├── test_reports.py    # Report endpoint tests
│   └── test_etl.py        # ETL endpoint tests
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start

### 1. Clone & install dependencies

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and at minimum set a strong SECRET_KEY
```

### 3. Run the API

```bash
uvicorn app.main:app --reload
```

Interactive docs → **http://localhost:8000/docs**

---

## API Reference

### Health

| Method | Path | Description |
|---|---|---|
| GET | `/` | Root health check |
| GET | `/health` | Liveness probe |

### Authentication (`/auth`)

| Method | Path | Auth required | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Register a new user |
| POST | `/auth/login` | No | Get access + refresh tokens |
| POST | `/auth/refresh` | No | Exchange refresh token for new access token |
| POST | `/auth/logout` | No | Revoke a refresh token |
| POST | `/auth/logout-all` | Bearer | Revoke all tokens for the current user |
| GET | `/auth/me` | Bearer | Get current user profile |

#### Register

```json
POST /auth/register
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "Secure123",
  "full_name": "John Doe"
}
```

#### Login

```json
POST /auth/login
{
  "username": "john_doe",
  "password": "Secure123"
}
// Response: { "access_token": "...", "refresh_token": "...", "token_type": "bearer" }
```

Use `Authorization: Bearer <access_token>` on protected endpoints.

---

### Reports (`/reports`)

| Method | Path | Auth required | Description |
|---|---|---|---|
| GET | `/reports/sessions/excel` | Bearer | Download pose sessions as `.xlsx` |

Query params (superuser only): `?user_id=<int>` — filter by specific user; omit for all users.

---

### ETL (`/etl`)

| Method | Path | Auth required | Description |
|---|---|---|---|
| GET | `/etl/pipelines` | Bearer | List available ETL pipelines |
| POST | `/etl/trigger` | Superuser Bearer | Trigger an ETL pipeline |

#### Trigger payload

```json
POST /etl/trigger
{
  "pipeline": "pose_sessions_to_dw",
  "parameters": { "date": "2024-01-15" },
  "async_run": true
}
```

Available pipelines:
- `pose_sessions_to_dw` — Load raw sessions into the data warehouse
- `keypoints_aggregation` — Aggregate keypoint metrics per user per day
- `user_activity_summary` — Compute weekly activity summaries
- `full_etl_refresh` — Full refresh (all pipelines in order)

---

## Running Tests

```bash
pytest tests/ -v
```

All 26 tests cover auth flows, Excel generation, and ETL triggers using an in-memory SQLite database.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | *(required in prod)* | JWT signing key |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `DATABASE_URL` | `sqlite:///./pose.db` | SQLAlchemy database URL |
| `ETL_BASE_URL` | `http://localhost:8001` | Base URL of ETL service |
| `ETL_API_KEY` | *(empty)* | API key forwarded to ETL service |

---

## Security Notes

- Passwords are hashed with **bcrypt** (no plain-text storage).
- Refresh tokens are stored in the database and can be individually or bulk-revoked.
- All sensitive environment values should be set via `.env` or injected by your deployment platform — **never committed to source control**.
- The `SECRET_KEY` should be a cryptographically random string of at least 32 characters in production.
