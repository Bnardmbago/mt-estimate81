import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.calculation.schemas import RateCardSettings


class RateCardUpdate(BaseModel):
    settings: RateCardSettings


class RateCardVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rate_card_id: uuid.UUID
    version_number: int
    settings: dict
    created_at: datetime


class ActiveRateCardResponse(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool
    version_number: int
    version_id: uuid.UUID
    settings: dict
    created_at: datetime
