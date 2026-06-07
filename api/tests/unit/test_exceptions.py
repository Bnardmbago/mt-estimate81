from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.calculation.engine import CalculationError
from app.exceptions import (
    AppError,
    app_error_handler,
    calculation_error_handler,
    http_exception_handler,
)


@pytest.mark.asyncio
async def test_app_error_handler_shape():
    exc = AppError("Estimate not found", "ESTIMATE_NOT_FOUND", status_code=404)
    response = await app_error_handler(MagicMock(), exc)

    assert response.status_code == 404
    assert response.body == (
        b'{"error":"Estimate not found","code":"ESTIMATE_NOT_FOUND","details":{}}'
    )


@pytest.mark.asyncio
async def test_calculation_error_maps_to_unknown_role():
    exc = CalculationError("Unknown role 'qa'", feature_item_name="Auth module")
    response = await calculation_error_handler(MagicMock(), exc)

    assert response.status_code == 400
    payload = response.body.decode()
    assert '"code":"UNKNOWN_ROLE"' in payload
    assert '"feature_item_name":"Auth module"' in payload


@pytest.mark.asyncio
async def test_http_exception_normalization():
    exc = HTTPException(
        status_code=403,
        detail={"error": "Forbidden", "code": "FORBIDDEN", "reason": "admin only"},
    )
    response = await http_exception_handler(MagicMock(), exc)

    assert response.status_code == 403
    payload = response.body.decode()
    assert '"error":"Forbidden"' in payload
    assert '"code":"FORBIDDEN"' in payload
    assert '"reason":"admin only"' in payload
