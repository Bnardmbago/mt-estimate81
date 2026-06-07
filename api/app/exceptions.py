from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.calculation.engine import CalculationError


class AppError(Exception):
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 400,
        details: dict | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def _error_payload(
    message: str,
    code: str,
    details: dict | None = None,
) -> dict:
    return {
        "error": message,
        "code": code,
        "details": details or {},
    }


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(exc.message, exc.code, exc.details),
    )


async def calculation_error_handler(_request: Request, exc: CalculationError) -> JSONResponse:
    details: dict = {}
    if exc.feature_item_name:
        details["feature_item_name"] = exc.feature_item_name
    return JSONResponse(
        status_code=400,
        content=_error_payload(str(exc), "UNKNOWN_ROLE", details),
    )


async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("error", str(detail))
        code = detail.get("code", "HTTP_ERROR")
        details = {
            key: value
            for key, value in detail.items()
            if key not in ("error", "code")
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(message, code, details),
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(str(detail), "HTTP_ERROR"),
    )
