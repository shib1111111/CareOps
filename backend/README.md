# CareOps Backend API

FastAPI backend for the **CareOps AI** decision-support platform.

The API exposes typed assessment contracts, executes CareOps assessment workflows, and provides access to persisted decision results.

## Architecture

```text
Client
  ↓
FastAPI
  ↓
Application Layer
  ↓
Assessment / Domain Logic
  ↓
AI Orchestration
  ↓
Persistence
```

The backend keeps API concerns separate from domain logic, AI execution, and persistence.

## API

| Method | Endpoint                   | Purpose                |
| ------ | -------------------------- | ---------------------- |
| `GET`  | `/health`                  | Liveness check         |
| `GET`  | `/ready`                   | Readiness check        |
| `POST` | `/api/v1/assessments`      | Create an assessment   |
| `GET`  | `/api/v1/assessments/{id}` | Retrieve an assessment |

Interactive API documentation is available at:

```text
/docs
/redoc
```

## Project Structure

```text
backend/
├── api.py          # FastAPI application and routes
├── schemas.py      # Request / response contracts
└── README.md
```

The backend delegates business logic to the core `careops` package rather than implementing domain rules inside API routes.

## Run Locally

From the project root:

```bash
uv sync
uv run uvicorn backend.api:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

## Configuration

Create the environment file from the provided template:

```bash
cp .env.example .env
```

Configure the required AI provider credentials and runtime settings.

Keep secrets outside source control.

## Design Principles

* **Typed contracts** — Pydantic request and response models.
* **Thin API layer** — routes delegate to application services.
* **Deterministic decisions** — business findings originate from explicit rules.
* **Evidence-backed AI** — AI operates on structured assessment results.
* **Traceable execution** — assessments retain findings, actions, and run metadata.
* **Provider abstraction** — AI infrastructure remains decoupled from API contracts.

> CareOps is a proof of concept using demonstration data and policies. It is not intended to independently diagnose, treat, or make clinical decisions.
