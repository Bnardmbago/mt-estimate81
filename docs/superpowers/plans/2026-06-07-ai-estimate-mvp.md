# AI Estimate MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an internal bilingual (JP/EN) web app that generates software project estimates from form input and uploaded documents, with AI extraction, deterministic NRC/RC calculation, triple-format export, and estimate-vs-actual variance tracking.

**Architecture:** Next.js 15 frontend + FastAPI backend in Docker Compose on an office server. Hermes Agent sidecar extracts document text locally; a provider-agnostic AI layer (OpenAI default) produces structured requirements and feature hours; a pure Python calculation engine computes JPY costs. PostgreSQL stores all data; local volumes for files (GCS-ready abstraction).

**Tech Stack:** Next.js 15, React, next-intl, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, Pydantic v2, pytest, httpx, openpyxl, WeasyPrint, Jinja2, bcrypt, PyJWT, Hermes Agent, Docker Compose, nginx

**Design spec:** `docs/superpowers/specs/2026-06-07-ai-estimate-mvp-design.md`

---

## File Structure

```text
ai_estimate_V2/
├── docker-compose.yml
├── .env.example
├── nginx/nginx.conf
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/versions/
│   ├── scripts/seed_admin.py
│   ├── app/
│   │   ├── main.py                 # FastAPI app, router registration
│   │   ├── config.py               # Settings from env (pydantic-settings)
│   │   ├── database.py             # SQLAlchemy engine + session
│   │   ├── dependencies.py         # get_db, get_current_user
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── estimate.py
│   │   │   ├── rate_card.py
│   │   │   └── audit.py
│   │   ├── schemas/                # Pydantic request/response DTOs
│   │   ├── auth/                   # login, JWT, password hashing
│   │   ├── estimates/              # CRUD, lifecycle, status polling
│   │   ├── documents/              # upload, Hermes client, extraction
│   │   ├── ai/                     # provider abstraction + adapters
│   │   ├── calculation/            # pure NRC/RC engine
│   │   ├── exports/                # PDF, Excel, Markdown generators
│   │   ├── admin/                  # rate cards, users, system health
│   │   ├── feedback/               # actuals + variance
│   │   ├── audit/                  # append-only change log service
│   │   └── storage/                # LocalStorageBackend (+ GCS stub)
│   └── tests/
│       ├── conftest.py
│       ├── unit/
│       └── integration/
└── web/
    ├── Dockerfile
    ├── package.json
    ├── next.config.ts
    ├── middleware.ts               # next-intl locale routing
    ├── messages/ja.json
    ├── messages/en.json
    ├── app/
    │   ├── [locale]/layout.tsx
    │   ├── [locale]/login/page.tsx
    │   ├── [locale]/estimates/page.tsx
    │   ├── [locale]/estimates/new/page.tsx
    │   ├── [locale]/estimates/[id]/page.tsx
    │   ├── [locale]/admin/page.tsx
    │   └── api/[...path]/route.ts  # proxy to FastAPI
    ├── components/
    │   ├── EstimateForm.tsx        # 21-field questionnaire
    │   ├── FeatureItemEditor.tsx
    │   ├── CalculationBreakdown.tsx
    │   ├── ExportPanel.tsx
    │   ├── VarianceReport.tsx
    │   └── admin/
    └── lib/api.ts                  # typed fetch wrapper
```

---

## Phase 1: Foundation

### Task 1: Docker Compose & project scaffold

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `api/Dockerfile`
- Create: `web/Dockerfile`
- Create: `nginx/nginx.conf`

- [ ] **Step 1: Create `.env.example`**

```env
POSTGRES_USER=estimate
POSTGRES_PASSWORD=change_me
POSTGRES_DB=ai_estimate
DATABASE_URL=postgresql+asyncpg://estimate:change_me@db:5432/ai_estimate

JWT_SECRET=change_me_to_random_64_chars
JWT_EXPIRY_HOURS=8

AI_PROVIDER=openai
AI_MODEL=gpt-4o
OPENAI_API_KEY=

HERMES_URL=http://hermes:8080
STORAGE_BACKEND=local
STORAGE_PATH=/data

DEFAULT_LOCALE=ja
APP_ENV=development
NEXT_PUBLIC_API_URL=http://api:8000
```

- [ ] **Step 2: Create `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: ./api
    env_file: .env
    volumes:
      - upload_data:/data/uploads
      - export_data:/data/exports
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8000:8000"

  web:
    build: ./web
    env_file: .env
    depends_on:
      - api
    ports:
      - "3000:3000"

  hermes:
    image: nousresearch/hermes-agent:latest
    env_file: .env
    volumes:
      - upload_data:/data/uploads:ro
    ports:
      - "8080:8080"

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
    depends_on:
      - web
      - api

volumes:
  postgres_data:
  upload_data:
  export_data:
```

- [ ] **Step 3: Create `api/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Create `api/requirements.txt`**

```text
fastapi==0.115.6
uvicorn[standard]==0.32.1
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
alembic==1.14.0
pydantic[email]==2.10.3
pydantic-settings==2.6.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
httpx==0.28.1
python-multipart==0.0.20
openpyxl==3.1.5
weasyprint==63.1
jinja2==3.1.4
openai==1.57.4
anthropic==0.40.0
pytest==8.3.4
pytest-asyncio==0.24.0
```

- [ ] **Step 5: Verify stack starts**

Run: `cp .env.example .env && docker compose up -d db`
Expected: `db` container healthy

- [ ] **Step 6: Commit**

```bash
git init
git add docker-compose.yml .env.example api/Dockerfile api/requirements.txt nginx/nginx.conf
git commit -m "chore: scaffold Docker Compose infrastructure"
```

---

### Task 2: FastAPI app shell + config

**Files:**
- Create: `api/app/config.py`
- Create: `api/app/main.py`
- Create: `api/app/database.py`
- Test: `api/tests/unit/test_health.py`

- [ ] **Step 1: Write the failing test**

```python
# api/tests/unit/test_health.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && pip install -r requirements.txt && pytest tests/unit/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError: app.main`

- [ ] **Step 3: Implement config, database, main**

```python
# api/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://estimate:change_me@localhost:5432/ai_estimate"
    jwt_secret: str = "dev-secret"
    jwt_expiry_hours: int = 8
    ai_provider: str = "openai"
    ai_model: str = "gpt-4o"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    hermes_url: str = "http://localhost:8080"
    storage_backend: str = "local"
    storage_path: str = "./data"
    default_locale: str = "ja"
    app_env: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()
```

```python
# api/app/database.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.app_env == "development")
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as session:
        yield session
```

```python
# api/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Estimate API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd api && pytest tests/unit/test_health.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api/app/ api/tests/
git commit -m "feat: add FastAPI app shell with health endpoint"
```

---

### Task 3: Database models + initial migration

**Files:**
- Create: `api/app/models/__init__.py`, `user.py`, `estimate.py`, `rate_card.py`, `audit.py`
- Create: `api/alembic.ini`, `api/alembic/env.py`
- Create: `api/alembic/versions/001_initial_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# api/tests/unit/test_models_import.py
from app.models.user import User
from app.models.estimate import Estimate, EstimateStatus
from app.models.rate_card import RateCard, RateCardVersion

def test_estimate_status_values():
    assert EstimateStatus.DRAFT.value == "draft"
    assert EstimateStatus.COMPLETED.value == "completed"
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `cd api && pytest tests/unit/test_models_import.py -v`

- [ ] **Step 3: Implement models**

```python
# api/app/models/user.py
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_locale: Mapped[str] = mapped_column(String(2), default="ja")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

```python
# api/app/models/estimate.py
import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class EstimateStatus(str, enum.Enum):
    DRAFT = "draft"
    EXTRACTING = "extracting"
    REVIEW = "review"
    CALCULATED = "calculated"
    EXPORTED = "exported"
    COMPLETED = "completed"

class Estimate(Base):
    __tablename__ = "estimates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_name: Mapped[str] = mapped_column(String(255))
    client_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default=EstimateStatus.DRAFT.value)
    locale: Mapped[str] = mapped_column(String(2), default="ja")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    rate_card_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rate_card_versions.id"), nullable=True)
    form_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    extracted_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    calculation_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    maintenance_assumptions: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("EstimateDocument", back_populates="estimate", cascade="all, delete-orphan")
    feature_items = relationship("FeatureItem", back_populates="estimate", cascade="all, delete-orphan")

class EstimateDocument(Base):
    __tablename__ = "estimate_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estimate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("estimates.id"))
    original_filename: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(10))
    storage_path: Mapped[str] = mapped_column(String(1024))
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[str] = mapped_column(String(20), default="pending")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    estimate = relationship("Estimate", back_populates="documents")

class FeatureItem(Base):
    __tablename__ = "feature_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estimate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("estimates.id"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    hours: Mapped[float] = mapped_column(Numeric(10, 2))
    phase: Mapped[str] = mapped_column(String(50))
    role: Mapped[str] = mapped_column(String(50))
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    estimate = relationship("Estimate", back_populates="feature_items")
```

Implement `RateCard`, `RateCardVersion`, `Export`, `Actuals`, `AuditLog` models following design spec section 5.2 (same pattern as above).

- [ ] **Step 4: Generate Alembic migration**

Run: `cd api && alembic init alembic && alembic revision --autogenerate -m "initial_schema" && alembic upgrade head`
Expected: All tables created

- [ ] **Step 5: Run model test — PASS**

- [ ] **Step 6: Commit**

```bash
git add api/app/models/ api/alembic/
git commit -m "feat: add database models and initial migration"
```

---

### Task 4: Auth module (JWT + login)

**Files:**
- Create: `api/app/auth/service.py`, `api/app/auth/router.py`
- Create: `api/app/dependencies.py`
- Create: `api/scripts/seed_admin.py`
- Test: `api/tests/unit/test_auth.py`

- [ ] **Step 1: Write failing test**

```python
# api/tests/unit/test_auth.py
from passlib.context import CryptContext
from app.auth.service import hash_password, verify_password, create_access_token, decode_access_token

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def test_password_hash_roundtrip():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)

def test_jwt_roundtrip():
    token = create_access_token({"sub": "user-id"})
    payload = decode_access_token(token)
    assert payload["sub"] == "user-id"
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement auth service**

```python
# api/app/auth/service.py
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
```

```python
# api/app/auth/router.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.auth.service import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    user: dict

@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail={"error": "Invalid credentials", "code": "AUTH_INVALID"})
    token = create_access_token({"sub": str(user.id), "is_admin": user.is_admin})
    return LoginResponse(
        access_token=token,
        user={"id": str(user.id), "email": user.email, "display_name": user.display_name,
              "is_admin": user.is_admin, "preferred_locale": user.preferred_locale},
    )
```

Register router in `main.py`: `from app.auth.router import router as auth_router; app.include_router(auth_router)`

- [ ] **Step 4: Create seed script**

```python
# api/scripts/seed_admin.py
import asyncio
from sqlalchemy import select
from app.database import SessionLocal
from app.models.user import User
from app.auth.service import hash_password

async def main():
    async with SessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == "admin@example.com"))
        if existing.scalar_one_or_none():
            print("Admin already exists")
            return
        admin = User(
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            display_name="Admin",
            is_admin=True,
            preferred_locale="ja",
        )
        db.add(admin)
        await db.commit()
        print("Admin created: admin@example.com / admin123")

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 5: Run tests — PASS**

- [ ] **Step 6: Commit**

```bash
git add api/app/auth/ api/scripts/seed_admin.py api/tests/unit/test_auth.py
git commit -m "feat: add JWT auth and login endpoint"
```

---

### Task 5: Next.js shell + i18n + API proxy

**Files:**
- Create: `web/package.json`, `web/next.config.ts`, `web/middleware.ts`
- Create: `web/messages/ja.json`, `web/messages/en.json`
- Create: `web/app/[locale]/layout.tsx`, `web/app/[locale]/login/page.tsx`
- Create: `web/app/api/[...path]/route.ts`

- [ ] **Step 1: Scaffold Next.js**

Run: `cd web && npx create-next-app@latest . --typescript --tailwind --app --no-eslint --src-dir=false --import-alias="@/*"`

- [ ] **Step 2: Install next-intl**

Run: `cd web && npm install next-intl`

- [ ] **Step 3: Create message files** (keys for nav, login, estimates — start minimal)

```json
// web/messages/ja.json
{
  "nav": { "estimates": "見積一覧", "admin": "管理", "logout": "ログアウト" },
  "login": { "title": "ログイン", "email": "メール", "password": "パスワード", "submit": "ログイン" },
  "estimates": { "new": "新規見積", "list": "見積一覧" }
}
```

```json
// web/messages/en.json
{
  "nav": { "estimates": "Estimates", "admin": "Admin", "logout": "Logout" },
  "login": { "title": "Login", "email": "Email", "password": "Password", "submit": "Sign in" },
  "estimates": { "new": "New Estimate", "list": "Estimates" }
}
```

- [ ] **Step 4: API proxy route**

```typescript
// web/app/api/[...path]/route.ts
import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function proxy(req: NextRequest, { params }: { params: { path: string[] } }) {
  const path = params.path.join("/");
  const url = `${API_URL}/${path}${req.nextUrl.search}`;
  const headers = new Headers(req.headers);
  headers.delete("host");
  const res = await fetch(url, { method: req.method, headers, body: req.body, duplex: "half" } as RequestInit);
  return new NextResponse(res.body, { status: res.status, headers: res.headers });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
```

- [ ] **Step 5: Login page** calling `POST /api/auth/login`, store token in httpOnly cookie via route handler wrapper

- [ ] **Step 6: Verify**

Run: `docker compose up -d && open http://localhost/login`
Expected: Bilingual login page renders; locale toggle works

- [ ] **Step 7: Commit**

```bash
git add web/
git commit -m "feat: add Next.js shell with i18n and API proxy"
```

---

## Phase 2: Form & Estimates

### Task 6: Estimate CRUD + audit log

**Files:**
- Create: `api/app/audit/service.py`
- Create: `api/app/estimates/router.py`, `api/app/estimates/service.py`
- Create: `api/app/schemas/estimate.py`
- Test: `api/tests/integration/test_estimates_crud.py`

- [ ] **Step 1: Write failing integration test**

```python
# api/tests/integration/test_estimates_crud.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_create_and_list_estimate(auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create = await client.post("/estimates", json={
            "project_name": "Test Project",
            "client_name": "ACME",
            "locale": "en",
        }, headers=auth_headers)
        assert create.status_code == 201
        estimate_id = create.json()["id"]

        get = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
        assert get.status_code == 200
        assert get.json()["project_name"] == "Test Project"
        assert get.json()["status"] == "draft"
```

- [ ] **Step 2: Implement audit service**

```python
# api/app/audit/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog

async def log_change(db: AsyncSession, estimate_id, user_id, action: str, changes: dict):
    entry = AuditLog(estimate_id=estimate_id, user_id=user_id, action=action, changes=changes)
    db.add(entry)
    await db.flush()
```

- [ ] **Step 3: Implement estimate router** with endpoints:
  - `POST /estimates` — create draft
  - `GET /estimates` — list all (internal transparency)
  - `GET /estimates/{id}` — detail
  - `PATCH /estimates/{id}` — update form_data, project_name, client_name, locale
  - `GET /estimates/{id}/audit` — audit timeline

Each mutating endpoint calls `log_change`.

- [ ] **Step 4: Run integration test — PASS**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add estimate CRUD with audit logging"
```

---

### Task 7: 21-field estimate form (UI)

**Files:**
- Create: `web/components/EstimateForm.tsx`
- Create: `web/lib/formFields.ts` (field definitions from `questionnaire_form.md`)
- Modify: `web/app/[locale]/estimates/new/page.tsx`
- Modify: `web/app/[locale]/estimates/[id]/page.tsx`

- [ ] **Step 1: Define form fields**

```typescript
// web/lib/formFields.ts
export const FORM_FIELDS = [
  { key: "project_name", required: true, type: "text" },
  { key: "nature_of_work", required: true, type: "textarea" },
  { key: "scope_boundaries", required: true, type: "textarea" },
  { key: "project_overview", required: true, type: "textarea" },
  { key: "system_type", required: true, type: "text" },
  { key: "business_domain", required: true, type: "text" },
  { key: "main_functional_needs", required: true, type: "textarea" },
  { key: "non_functional_needs", required: true, type: "textarea" },
  { key: "users_and_load", required: true, type: "textarea" },
  { key: "integrations", required: true, type: "textarea" },
  { key: "data_complexity", required: true, type: "select", options: ["simple", "moderate", "complex"] },
  { key: "ui_complexity", required: true, type: "select", options: ["low", "medium", "high"] },
  { key: "technology_preferences", required: false, type: "textarea" },
  { key: "development_approach", required: true, type: "text" },
  { key: "rules_and_standards", required: true, type: "textarea" },
  { key: "team_and_resources", required: true, type: "textarea" },
  { key: "development_location", required: true, type: "select", options: ["japan", "offshore", "hybrid"] },
  { key: "delivery_timing", required: true, type: "textarea" },
  { key: "maintenance_support", required: true, type: "textarea" },
  { key: "risks_unknowns", required: true, type: "textarea" },
  { key: "budget", required: false, type: "text" },
] as const;
```

Add i18n label keys in `ja.json` / `en.json` for each field (e.g. `form.project_name`, `form.nature_of_work`, …).

- [ ] **Step 2: Build `EstimateForm` component** — renders all fields, validates required, calls `PATCH /api/estimates/{id}` on save

- [ ] **Step 3: Wire into estimate detail page** with Save button and unsaved-changes indicator

- [ ] **Step 4: Manual verify** — create estimate, fill all 21 fields, reload page, data persists

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add 21-field bilingual estimate form"
```

---

## Phase 3: Documents + Hermes

### Task 8: Local storage backend

**Files:**
- Create: `api/app/storage/base.py`, `api/app/storage/local.py`
- Test: `api/tests/unit/test_storage.py`

- [ ] **Step 1: Write failing test**

```python
# api/tests/unit/test_storage.py
import pytest
from app.storage.local import LocalStorageBackend

@pytest.mark.asyncio
async def test_save_and_read_file(tmp_path):
    storage = LocalStorageBackend(base_path=str(tmp_path))
    path = await storage.save("uploads/test.pdf", b"pdf-content")
    assert await storage.read(path) == b"pdf-content"
    assert await storage.exists(path)
```

- [ ] **Step 2-4: Implement `StorageBackend` protocol and `LocalStorageBackend`**

```python
# api/app/storage/base.py
from typing import Protocol

class StorageBackend(Protocol):
    async def save(self, relative_path: str, content: bytes) -> str: ...
    async def read(self, storage_path: str) -> bytes: ...
    async def exists(self, storage_path: str) -> bool: ...
    async def delete(self, storage_path: str) -> None: ...
```

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add local file storage backend"
```

---

### Task 9: Document upload + Hermes extraction client

**Files:**
- Create: `api/app/documents/hermes_client.py`
- Create: `api/app/documents/extractor.py` (TXT/MD direct read fallback)
- Create: `api/app/documents/router.py`
- Test: `api/tests/unit/test_document_extractor.py`

- [ ] **Step 1: Write failing test with mocked Hermes**

```python
# api/tests/unit/test_document_extractor.py
from unittest.mock import AsyncMock, patch
import pytest
from app.documents.extractor import extract_document_text

@pytest.mark.asyncio
async def test_extract_txt_direct():
    text = await extract_document_text("/data/test.txt", "txt", hermes_client=None)
    # For txt, reads file directly — test with tmp file
    assert isinstance(text, str)

@pytest.mark.asyncio
async def test_extract_pdf_via_hermes():
    mock_hermes = AsyncMock(return_value={"markdown": "# Title\nContent", "page_count": 1, "method": "pymupdf"})
    with patch("builtins.open", create=True):
        result = await extract_document_text("/data/test.pdf", "pdf", hermes_client=mock_hermes)
    assert "Content" in result
```

- [ ] **Step 2: Implement Hermes client**

```python
# api/app/documents/hermes_client.py
import httpx
from app.config import settings

class HermesClient:
    def __init__(self, base_url: str = settings.hermes_url):
        self.base_url = base_url

    async def extract(self, file_path: str, file_type: str) -> dict:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/internal/extract",
                json={"file_path": file_path, "file_type": file_type},
            )
            response.raise_for_status()
            return response.json()
```

- [ ] **Step 3: Implement document router**

Endpoints:
- `POST /estimates/{id}/documents` — multipart upload, save to storage, create `EstimateDocument` record
- `DELETE /estimates/{id}/documents/{doc_id}` — remove file + record
- `POST /estimates/{id}/documents/{doc_id}/retry` — re-extract single failed doc

- [ ] **Step 4: UI upload component** on estimate detail page with drag-drop, file list, status badges (pending/processing/done/failed)

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add document upload and Hermes extraction pipeline"
```

---

## Phase 4: AI Extraction

### Task 10: AI schemas + provider abstraction

**Files:**
- Create: `api/app/ai/schemas.py`
- Create: `api/app/ai/provider.py`
- Create: `api/app/ai/openai_adapter.py`
- Create: `api/app/ai/anthropic_adapter.py`
- Create: `api/app/ai/factory.py`
- Test: `api/tests/unit/test_ai_schemas.py`

- [ ] **Step 1: Write failing schema test**

```python
# api/tests/unit/test_ai_schemas.py
import pytest
from pydantic import ValidationError
from app.ai.schemas import ExtractedRequirements, FeatureItemSuggestion

def test_valid_extraction_payload():
    data = ExtractedRequirements(
        functional_requirements=["Login"],
        non_functional_requirements=["99.9% uptime"],
        user_roles=["Admin"],
        modules=["Auth"],
        external_systems=[],
        risks=["Tight deadline"],
        gaps=["Budget unclear"],
        confidence_notes="High confidence on auth scope",
        feature_items=[
            FeatureItemSuggestion(name="Login", description="OAuth login", suggested_hours=40, phase="development", role="developer")
        ],
        maintenance_assumptions={"monthly_support_hours": 20, "notes": "Business hours support"},
    )
    assert len(data.feature_items) == 1

def test_invalid_feature_item_rejected():
    with pytest.raises(ValidationError):
        FeatureItemSuggestion(name="", description="", suggested_hours=-1, phase="dev", role="dev")
```

- [ ] **Step 2: Implement schemas**

```python
# api/app/ai/schemas.py
from pydantic import BaseModel, Field

class FeatureItemSuggestion(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    suggested_hours: float = Field(gt=0)
    phase: str
    role: str

class MaintenanceAssumptions(BaseModel):
    monthly_support_hours: float = Field(ge=0, default=0)
    notes: str = ""

class ExtractedRequirements(BaseModel):
    functional_requirements: list[str]
    non_functional_requirements: list[str]
    user_roles: list[str]
    modules: list[str]
    external_systems: list[str]
    risks: list[str]
    gaps: list[str]
    confidence_notes: str
    feature_items: list[FeatureItemSuggestion]
    maintenance_assumptions: MaintenanceAssumptions
```

- [ ] **Step 3: Implement OpenAI adapter** using `response_format` JSON schema mode, 90s timeout, locale-aware system prompt

- [ ] **Step 4: Implement factory**

```python
# api/app/ai/factory.py
from app.config import settings
from app.ai.openai_adapter import OpenAIProvider
from app.ai.anthropic_adapter import AnthropicProvider

def get_ai_provider():
    if settings.ai_provider == "anthropic":
        return AnthropicProvider(model=settings.ai_model, api_key=settings.anthropic_api_key)
    return OpenAIProvider(model=settings.ai_model, api_key=settings.openai_api_key)
```

- [ ] **Step 5: Run tests — PASS**

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: add AI provider abstraction with OpenAI and Anthropic adapters"
```

---

### Task 11: Extraction job + review UI

**Files:**
- Create: `api/app/estimates/extraction.py`
- Modify: `api/app/estimates/router.py` — add extract + status endpoints
- Create: `web/components/FeatureItemEditor.tsx`
- Create: `web/components/RequirementsReview.tsx`

- [ ] **Step 1: Implement extraction job**

```python
# api/app/estimates/extraction.py
async def run_extraction(db, estimate_id, user_id):
    # 1. Load estimate + documents + active rate card
    # 2. Set status = extracting
    # 3. Extract each pending document (parallel with asyncio.gather)
    # 4. Collect successful texts; note failures in confidence_notes
    # 5. Call AI provider with form_data + texts + locale
    # 6. On ValidationError: retry once with error appended to prompt
    # 7. Clear existing feature_items; insert new from AI response
    # 8. Save extracted_data + maintenance_assumptions
    # 9. Set status = review; log audit entry
```

- [ ] **Step 2: Add endpoints**
  - `POST /estimates/{id}/extract` — starts background task
  - `GET /estimates/{id}/status` — returns `{ status, extraction_progress }`
  - `PUT /estimates/{id}/feature-items` — bulk update line items
  - `PATCH /estimates/{id}/extracted-data` — edit requirements sections

- [ ] **Step 3: Review UI** — editable requirements lists, `FeatureItemEditor` table (name, hours, phase, role, add/remove rows), "Approve & Calculate" button

- [ ] **Step 4: Integration test with mocked AI**

```python
@pytest.mark.asyncio
async def test_extraction_populates_feature_items(mock_ai_provider, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create = await client.post("/estimates", json={
            "project_name": "Extract Test",
            "client_name": "ACME",
            "locale": "en",
        }, headers=auth_headers)
        estimate_id = create.json()["id"]

        await client.patch(f"/estimates/{estimate_id}", json={
            "form_data": {"main_functional_needs": "User login and dashboard"}
        }, headers=auth_headers)

        with patch("app.ai.factory.get_ai_provider", return_value=mock_ai_provider):
            extract = await client.post(f"/estimates/{estimate_id}/extract", headers=auth_headers)
            assert extract.status_code == 202

        # Poll until review (test uses synchronous extraction override)
        detail = await client.get(f"/estimates/{estimate_id}", headers=auth_headers)
        assert detail.json()["status"] == "review"
        assert len(detail.json()["feature_items"]) >= 1
```

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add AI extraction job and review UI"
```

---

## Phase 5: Calculation + Rate Cards

### Task 12: Calculation engine (TDD)

**Files:**
- Create: `api/app/calculation/engine.py`
- Create: `api/app/calculation/schemas.py`
- Test: `api/tests/unit/test_calculation_engine.py`

- [ ] **Step 1: Write failing tests (full suite)**

```python
# api/tests/unit/test_calculation_engine.py
import pytest
from app.calculation.engine import calculate_estimate, CalculationError
from app.calculation.schemas import FeatureItemInput, RateCardSettings

SAMPLE_RATE_CARD = RateCardSettings(
    roles=[
        {"name": "PM", "hourly_rate_jpy": 8000},
        {"name": "developer", "hourly_rate_jpy": 6000},
        {"name": "QA", "hourly_rate_jpy": 5000},
    ],
    phases=[
        {"name": "requirement", "percentage": 0.10},
        {"name": "design", "percentage": 0.15},
        {"name": "development", "percentage": 0.40},
        {"name": "testing", "percentage": 0.25},
        {"name": "deployment", "percentage": 0.10},
    ],
    contingency_rate=0.15,
    overhead_rate=0.10,
    monthly_rc_items=[{"name": "hosting", "amount_jpy": 50000}],
    setup_costs={"infrastructure_jpy": 300000, "tooling_jpy": 100000, "third_party_jpy": 0},
    productivity={"hours_per_feature_default": 40},
    tax_rate=0.10,
)

def test_basic_nrc_calculation():
    items = [
        FeatureItemInput(name="Auth", hours=40, phase="development", role="developer"),
        FeatureItemInput(name="PM work", hours=20, phase="requirement", role="PM"),
    ]
    maintenance = {"monthly_support_hours": 20, "support_role": "developer"}
    result = calculate_estimate(items, SAMPLE_RATE_CARD, maintenance, rate_card_version_id="v1")
    assert result.total_effort_hours == 60
    assert result.total_effort_days == 7.5  # 60 / 8
    assert result.nrc["labor_jpy"] == 40 * 6000 + 20 * 8000  # 400000
    assert result.nrc["contingency_jpy"] == int(result.nrc["labor_jpy"] * 0.15)
    assert result.rc["monthly_total_jpy"] == 50000 + 20 * 6000

def test_unknown_role_raises():
    items = [FeatureItemInput(name="Bad", hours=10, phase="development", role="unknown")]
    with pytest.raises(CalculationError) as exc:
        calculate_estimate(items, SAMPLE_RATE_CARD, {}, "v1")
    assert "unknown" in str(exc.value).lower()
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement engine**

```python
# api/app/calculation/engine.py
HOURS_PER_EFFORT_DAY = 8

class CalculationError(Exception):
    def __init__(self, message: str, feature_item_name: str | None = None):
        self.feature_item_name = feature_item_name
        super().__init__(message)

def calculate_estimate(feature_items, rate_card: RateCardSettings, maintenance: dict, rate_card_version_id: str):
    role_rates = {r["name"]: r["hourly_rate_jpy"] for r in rate_card.roles}
    role_hours: dict[str, float] = {}
    total_hours = 0.0

    for item in feature_items:
        if item.role not in role_rates:
            raise CalculationError(f"Unknown role '{item.role}'", feature_item_name=item.name)
        total_hours += float(item.hours)
        role_hours[item.role] = role_hours.get(item.role, 0) + float(item.hours)

    total_days = total_hours / HOURS_PER_EFFORT_DAY

    phase_breakdown = [
        {"phase": p["name"], "hours": round(total_hours * p["percentage"], 2), "percentage": p["percentage"]}
        for p in rate_card.phases
    ]

    role_breakdown = [
        {"role": role, "hours": hours, "rate_jpy": role_rates[role], "cost_jpy": int(hours * role_rates[role])}
        for role, hours in role_hours.items()
    ]

    labor_jpy = sum(r["cost_jpy"] for r in role_breakdown)
    contingency_jpy = int(labor_jpy * rate_card.contingency_rate)
    overhead_jpy = int(labor_jpy * rate_card.overhead_rate)
    setup_jpy = sum(rate_card.setup_costs.values())
    nrc_total = labor_jpy + setup_jpy + contingency_jpy + overhead_jpy

    support_role = maintenance.get("support_role", "developer")
    maintenance_jpy = int(maintenance.get("monthly_support_hours", 0) * role_rates.get(support_role, 0))
    monthly_rc = sum(i["amount_jpy"] for i in rate_card.monthly_rc_items) + maintenance_jpy

    return CalculationResult(
        total_effort_hours=total_hours,
        total_effort_days=total_days,
        phase_breakdown=phase_breakdown,
        role_breakdown=role_breakdown,
        nrc={"labor_jpy": labor_jpy, "setup_jpy": setup_jpy, "contingency_jpy": contingency_jpy,
             "overhead_jpy": overhead_jpy, "total_jpy": nrc_total},
        rc={"monthly_items": rate_card.monthly_rc_items, "maintenance_jpy": maintenance_jpy,
            "monthly_total_jpy": monthly_rc, "annual_total_jpy": monthly_rc * 12},
        first_year_total_jpy=nrc_total + monthly_rc * 12,
        rate_card_version_id=rate_card_version_id,
    )
```

- [ ] **Step 4: Run full test suite — PASS (≥80% coverage on calculation module)**

Run: `cd api && pytest tests/unit/test_calculation_engine.py -v --cov=app/calculation --cov-report=term-missing`

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add deterministic NRC/RC calculation engine"
```

---

### Task 13: Rate card admin + calculate endpoint

**Files:**
- Create: `api/app/admin/rate_cards.py`
- Modify: `api/app/estimates/router.py` — `POST /estimates/{id}/calculate`
- Create: `web/components/CalculationBreakdown.tsx`
- Create: `web/components/admin/RateCardEditor.tsx`

- [ ] **Step 1: Rate card endpoints**
  - `GET /admin/rate-cards/active`
  - `PUT /admin/rate-cards` — validates phase sum = 100%, creates new version
  - `GET /admin/rate-cards/versions`

- [ ] **Step 2: Calculate endpoint** — snapshots rate card on first calculate, runs engine, saves `calculation_result`, status → `calculated`

- [ ] **Step 3: `CalculationBreakdown` UI** — tables for phase, role, NRC, RC, first-year total with formula tooltips

- [ ] **Step 4: Seed default rate card** in `seed_admin.py` (2026 Standard Rates with PM/Developer/QA from spec examples)

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add rate card admin and calculate endpoint"
```

---

## Phase 6: Exports

### Task 14: Markdown export

**Files:**
- Create: `api/app/exports/templates/estimate.md.j2`
- Create: `api/app/exports/markdown.py`
- Test: `api/tests/unit/test_export_markdown.py`

- [ ] **Step 1: Write failing test**

```python
def test_markdown_export_contains_nrc_total(sample_estimate_with_calculation):
    md = generate_markdown(sample_estimate_with_calculation, locale="en")
    assert "First Year Total" in md or "初年度合計" in md
    assert "¥" in md
```

- [ ] **Step 2: Create Jinja2 template** with locale blocks for JA/EN section headings

- [ ] **Step 3: Implement generator + `POST /estimates/{id}/export` with `{ "format": "md" }`**

- [ ] **Step 4: Commit**

---

### Task 15: Excel export

**Files:**
- Create: `api/app/exports/excel.py`
- Test: `api/tests/unit/test_export_excel.py`

- [ ] **Step 1: Test workbook has Summary + Features sheets with correct NRC total**

- [ ] **Step 2: Implement 7-sheet workbook** (Summary, Features, Phase, Role, NRC, RC, Assumptions) with Excel formulas on Role Breakdown sheet

- [ ] **Step 3: Commit**

---

### Task 16: PDF export

**Files:**
- Create: `api/app/exports/templates/estimate.html.j2`
- Create: `api/app/exports/pdf.py`

- [ ] **Step 1: HTML template** with Noto Sans JP `@font-face` in Docker image

- [ ] **Step 2: Add fonts to `api/Dockerfile`**

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends fonts-noto-cjk && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 3: WeasyPrint render + test** verifying PDF bytes start with `%PDF`

- [ ] **Step 4: `ExportPanel` UI** — format checkboxes, download links, stale export badge

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add PDF, Excel, and Markdown export generators"
```

---

## Phase 7: Feedback & Variance

### Task 17: Actuals + variance

**Files:**
- Create: `api/app/feedback/service.py`
- Create: `api/app/feedback/router.py`
- Create: `web/components/VarianceReport.tsx`
- Test: `api/tests/unit/test_variance.py`

- [ ] **Step 1: Write failing test**

```python
# api/tests/unit/test_variance.py
from app.feedback.service import compute_variance

def test_variance_percentage():
    result = compute_variance(
        estimated={"effort_hours": 640, "nrc_jpy": 4950000, "rc_monthly_jpy": 300000},
        actual={"effort_hours": 720, "nrc_jpy": 5400000, "rc_monthly_jpy": 280000},
    )
    assert result["effort_hours"]["variance_pct"] == 12.5
    assert result["effort_hours"]["severity"] == "amber"
    assert result["nrc_jpy"]["variance_pct"] == pytest.approx(9.09, rel=0.01)
    assert result["nrc_jpy"]["severity"] == "green"
```

- [ ] **Step 2: Implement variance service**

```python
def compute_variance(estimated: dict, actual: dict) -> dict:
    def row(key):
        est = estimated[key]
        act = actual[key]
        pct = ((act - est) / est * 100) if est else 0
        severity = "green" if abs(pct) <= 10 else "amber" if abs(pct) <= 25 else "red"
        return {"estimated": est, "actual": act, "variance_pct": round(pct, 1), "severity": severity}
    return {
        "effort_hours": row("effort_hours"),
        "effort_days": row("effort_days"),
        "nrc_jpy": row("nrc_jpy"),
        "rc_monthly_jpy": row("rc_monthly_jpy"),
    }
```

- [ ] **Step 3: Endpoints**
  - `POST /estimates/{id}/complete` — status → completed
  - `PUT /estimates/{id}/actuals`
  - `GET /estimates/variance-dashboard` — list completed with variance summary, sort/filter query params

- [ ] **Step 4: UI** — actuals form on completed estimates, `VarianceReport` table, team dashboard page at `/estimates/variance`

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add actuals entry and variance reporting"
```

---

## Phase 8: Admin, Polish & Smoke Tests

### Task 18: Admin panel (users + system health)

**Files:**
- Create: `api/app/admin/users.py`, `api/app/admin/system.py`
- Create: `web/app/[locale]/admin/page.tsx`

- [ ] **Step 1: User management endpoints** (admin-only dependency)
  - `POST /admin/users`
  - `PUT /admin/users/{id}/reset-password`
  - `PATCH /admin/users/{id}` — toggle is_admin, locale

- [ ] **Step 2: System health endpoint**

```python
@router.get("/admin/system/health")
async def system_health(db, hermes: HermesClient = Depends()):
    stuck = await count_estimates_stuck_extracting(db, minutes=10)
    return {
        "database": "ok",
        "hermes": await hermes.ping(),
        "ai_provider": settings.ai_provider,
        "ai_model": settings.ai_model,
        "stuck_extractions": stuck,
        "storage_usage_bytes": await storage.usage(),
    }
```

- [ ] **Step 3: Admin UI tabs** — Rate Cards, Users, AI Settings (read-only), System

- [ ] **Step 4: Commit**

---

### Task 19: Error handling polish

**Files:**
- Create: `api/app/exceptions.py`
- Modify: all routers to use consistent error shape

- [ ] **Step 1: Global exception handler**

```python
# api/app/exceptions.py
from fastapi import Request
from fastapi.responses import JSONResponse

class AppError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400, details: dict | None = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code, "details": exc.details},
    )
```

- [ ] **Step 2: Map `CalculationError` → code `UNKNOWN_ROLE`, AI timeout → `AI_TIMEOUT`**

- [ ] **Step 3: Add i18n error message keys in web messages files**

- [ ] **Step 4: Commit**

---

### Task 20: Manual smoke test checklist + README

**Files:**
- Create: `README.md`
- Create: `docs/smoke-test-checklist.md`

- [ ] **Step 1: Write README** with setup commands from design spec section 12.2

- [ ] **Step 2: Execute smoke checklist** (all items from design spec section 11 manual list)

- [ ] **Step 3: Fix any failures found**

- [ ] **Step 4: Final commit**

```bash
git commit -m "docs: add README and complete MVP smoke tests"
```

---

## Spec Coverage Self-Review

| Spec requirement | Task |
|------------------|------|
| Docker Compose office deployment | Task 1 |
| Next.js + FastAPI architecture | Tasks 1-5 |
| Auth (email/password, admin flag) | Task 4 |
| Bilingual UI (next-intl) | Task 5, 7 |
| 21-field form | Task 7 |
| Document upload (PDF/DOCX/XLSX/TXT/MD) | Task 9 |
| Hermes document extraction | Task 9 |
| AI provider abstraction (OpenAI/Anthropic) | Task 10 |
| Hybrid feature + hours extraction | Task 11 |
| Review/edit extracted data | Task 11 |
| Calculation engine (effort hours ÷ 8) | Task 12 |
| Rate card admin + versioning | Task 13 |
| NRC/RC/first-year calculation | Task 12-13 |
| PDF + Excel + Markdown export | Tasks 14-16 |
| Actuals + variance | Task 17 |
| Audit log | Task 6 |
| Admin users + system health | Task 18 |
| Error handling | Task 19 |
| Local storage → GCS-ready abstraction | Task 8 |
| Provider switch via .env | Task 10 |
| Stuck extraction detection | Task 18 |

**Gaps:** None — all MVP spec items mapped. Out-of-scope items (calendar schedule, SSO, charts) intentionally excluded.

---

## Execution Order Summary

```text
Phase 1 (Tasks 1-5)   → Login works, DB schema live
Phase 2 (Tasks 6-7)   → Create/edit estimates with form
Phase 3 (Tasks 8-9)   → Upload and extract documents
Phase 4 (Tasks 10-11) → AI extraction + review
Phase 5 (Tasks 12-13) → Calculate NRC/RC
Phase 6 (Tasks 14-16) → Export all formats
Phase 7 (Task 17)     → Actuals + variance
Phase 8 (Tasks 18-20) → Admin, polish, smoke tests
```

Each phase produces demoable, testable software independently.
