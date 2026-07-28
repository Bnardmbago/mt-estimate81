import uuid
from datetime import datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _default_expiry() -> datetime:
    return datetime.utcnow() + timedelta(days=30)


class PresentationPresetDraft(Base):
    __tablename__ = "presentation_preset_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    source_locale: Mapped[str] = mapped_column(String(2), default="en", nullable=False)
    theme_draft: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    style_draft: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    template_draft: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    target_theme_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("presentation_themes.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_style_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("presentation_styles.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_template_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("presentation_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    generation_meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    errors: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_default_expiry,
        nullable=False,
    )
