import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.admin.ai_settings import router as admin_ai_settings_router
from app.admin.discount_settings import router as admin_discount_settings_router
from app.admin.smtp_settings import router as admin_smtp_settings_router
from app.admin.system import router as admin_system_router
from app.admin.form_templates import public_router as form_templates_router
from app.admin.form_templates import router as admin_form_templates_router
from app.admin.users import router as admin_users_router
from app.auth.router import router as auth_router
from app.calculation.engine import CalculationError
from app.config import settings
from app.database import SessionLocal
from app.documents.router import router as documents_router
from app.estimates.router import router as estimates_router
from app.exceptions import (
    AppError,
    app_error_handler,
    calculation_error_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.exports.router import router as exports_router
from app.feedback.router import router as feedback_router
from app.fx import init_fx_service
from app.rate_cards.router import router as rate_cards_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    fx_service = init_fx_service(
        SessionLocal,
        refresh_interval_seconds=settings.fx_refresh_interval_seconds,
    )
    try:
        await fx_service.refresh_all()
    except Exception:
        logger.exception("Initial FX rate refresh failed")

    refresh_task = await fx_service.start_background_refresh()
    yield
    refresh_task.cancel()
    try:
        await refresh_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="AI Estimate API", version="0.1.0", lifespan=lifespan)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(CalculationError, calculation_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(auth_router)
app.include_router(feedback_router)
app.include_router(estimates_router)
app.include_router(documents_router)
app.include_router(rate_cards_router)
app.include_router(admin_ai_settings_router)
app.include_router(admin_discount_settings_router)
app.include_router(admin_smtp_settings_router)
app.include_router(admin_users_router)
app.include_router(admin_form_templates_router)
app.include_router(form_templates_router)
app.include_router(admin_system_router)
app.include_router(exports_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
