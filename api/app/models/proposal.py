import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProposalStatus(str, enum.Enum):
    GENERATING = "generating"
    DRAFT = "draft"
    READY = "ready"
    FINALIZED = "finalized"


class ProposalExportFormat(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    MD = "md"
    XLSX = "xlsx"


class ProposalExportVariant(str, enum.Enum):
    FULL = "full"
    ASSESSMENT = "assessment"
    PROPOSAL = "proposal"
    POC = "poc"


class Proposal(Base):
    __tablename__ = "proposals"
    __table_args__ = (UniqueConstraint("estimate_id", "locale", name="uq_proposals_estimate_locale"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estimate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estimates.id", ondelete="CASCADE"), index=True
    )
    locale: Mapped[str] = mapped_column(String(2), default="en")
    include_poc: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default=ProposalStatus.DRAFT.value)
    source_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    assessment: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    proposal_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    poc: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    diagrams: Mapped[list] = mapped_column(JSONB, default=list)
    milestones: Mapped[list] = mapped_column(JSONB, default=list)
    generation_meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    theme_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    style_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    template_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    presentation_meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    cover_values: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(128), default="")
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    exports = relationship(
        "ProposalExport",
        back_populates="proposal",
        cascade="all, delete-orphan",
        order_by="ProposalExport.generated_at.desc()",
    )


class ProposalExport(Base):
    __tablename__ = "proposal_exports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("proposals.id", ondelete="CASCADE"), index=True
    )
    format: Mapped[str] = mapped_column(String(16))
    variant: Mapped[str] = mapped_column(String(16), default=ProposalExportVariant.FULL.value)
    storage_path: Mapped[str] = mapped_column(String(1024))
    locale: Mapped[str] = mapped_column(String(2))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    theme_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    style_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    template_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(32), nullable=True)
    external_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    manually_edited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    generated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    proposal = relationship("Proposal", back_populates="exports")
