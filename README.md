# AI Estimate MVP

Internal web application that helps a small team generate software project estimates from client requirements. Users fill a 21-field form and/or upload documents; AI extracts requirements and suggests feature-level effort hours. A deterministic calculation engine produces NRC, RC, and first-year cost in JPY. Results export to PDF, Excel, and Markdown in Japanese or English.

**Stack:** Next.js 15 (web) · FastAPI (api) · PostgreSQL 16 · Hermes (document extraction) · Docker Compose

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [Node.js 20](https://nodejs.org/) (for local web development)
- [Python 3.12](https://www.python.org/) (for local API development)

## Quick Start (Docker)

**Start Docker Desktop first** — `docker compose` fails if the daemon is not running (`Cannot connect to the Docker daemon`).

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, JWT_SECRET, and AI API keys

# 2. Start all services
docker compose up -d --build

# 3. Run database migrations
docker compose exec api python -m alembic upgrade head

# 4. Seed admin user and default rate card
docker compose exec api python scripts/seed_admin.py
```

If you see `ModuleNotFoundError: No module named 'app'`, rebuild the API image first: `docker compose up -d --build api`

Open the app at [http://localhost](http://localhost) (nginx) or [http://localhost:3000](http://localhost:3000) (web directly).

### Default Admin Credentials

| Field | Value |
|-------|-------|
| Email | `admin@example.com` |
| Password | `admin123` |

**Change these credentials before deploying to production.**

## Local Development (without Docker)

Run PostgreSQL locally (or point `DATABASE_URL` at a remote instance), then start the API and web app separately.

### API

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # if not already done
# Set DATABASE_URL=postgresql+asyncpg://estimate:change_me@localhost:5432/ai_estimate
python -m alembic upgrade head
python scripts/seed_admin.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Web

```bash
cd web
npm install
# Set NEXT_PUBLIC_API_URL=http://localhost:8000 in .env
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## AI Provider Configuration

Switch between OpenAI and Anthropic via `.env` — no code changes required.

**OpenAI (default):**

```env
AI_PROVIDER=openai
AI_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

**Anthropic:**

```env
AI_PROVIDER=anthropic
AI_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...
```

Restart the API container (or uvicorn process) after changing provider settings.

## PDF Exports

One PDF export is available (Japanese or English via export locale):

| Format | Description |
|--------|-------------|
| **PDF (complete project estimate)** | Full estimate report for internal review or clients who need full transparency — executive summary, assumptions, features, NRC/RC breakdown, timeline, risks, approval, etc. |

Excel and Markdown exports include the same content as the PDF report.

## Services

| Service | Port | Purpose |
|---------|------|---------|
| nginx | 80 | Reverse proxy |
| web | 3000 | Next.js UI |
| api | 8000 | FastAPI backend |
| db | 5432 | PostgreSQL |
| hermes | 8080 | Local document text extraction sidecar (PDF, DOCX, XLSX) |

## Documentation

- [MVP Design Spec](docs/superpowers/specs/2026-06-07-ai-estimate-mvp-design.md)
- [Implementation Plan](docs/superpowers/plans/2026-06-07-ai-estimate-mvp.md)
- [Manual Smoke Test Checklist](docs/smoke-test-checklist.md)

## Testing

```bash
# API unit + integration tests
cd api && pytest -v

# Web production build
cd web && npm run build
```
