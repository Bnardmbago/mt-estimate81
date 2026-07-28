from datetime import datetime
from typing import Any, Literal

from sqlalchemy import DateTime, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

InstructionLocation = Literal[
    "ai_spec_assistant",
    "extraction",
    "extraction_client_constraints",
    "rate_card_generation",
    "rate_card_section",
    "proposal_assessment",
    "proposal_body",
    "proposal_poc",
]

InstructionLocale = Literal["en", "ja"]

INSTRUCTION_LOCATIONS: tuple[InstructionLocation, ...] = (
    "ai_spec_assistant",
    "extraction",
    "extraction_client_constraints",
    "rate_card_generation",
    "rate_card_section",
    "proposal_assessment",
    "proposal_body",
    "proposal_poc",
)

INSTRUCTION_LOCALES: tuple[InstructionLocale, ...] = ("en", "ja")


class AiInstructionLayer(Base):
    __tablename__ = "ai_instruction_layers"
    __table_args__ = (
        UniqueConstraint("location", "locale", name="uq_ai_instruction_layers_location_locale"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location: Mapped[str] = mapped_column(String(50), nullable=False)
    locale: Mapped[str] = mapped_column(String(2), nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
