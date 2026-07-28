import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstimateStatus(str, enum.Enum):
    DRAFT = "draft"
    EXTRACTING = "extracting"
    CONSTRAINT_PAUSED = "constraint_paused"
    REVIEW = "review"
    CALCULATED = "calculated"
    EXPORTED = "exported"
    COMPLETED = "completed"


class ExportFormat(str, enum.Enum):
    PDF = "pdf"
    PDF_QUOTATION = "pdf_quotation"
    XLSX = "xlsx"
    MD = "md"
    DOCX = "docx"
    DOCX_QUOTATION = "docx_quotation"
    PDF_INTERNAL = "pdf_internal"
    DOCX_INTERNAL = "docx_internal"
    XLSX_INTERNAL = "xlsx_internal"
    MD_INTERNAL = "md_internal"


class Estimate(Base):
    __tablename__ = "estimates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_name: Mapped[str] = mapped_column(String(255))
    client_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default=EstimateStatus.DRAFT.value)
    locale: Mapped[str] = mapped_column(String(2), default="ja")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    rate_card_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rate_card_versions.id"), nullable=True
    )
    rate_card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rate_cards.id"), nullable=True
    )
    form_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    form_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("form_templates.id"), nullable=True
    )
    form_schema_snapshot: Mapped[list] = mapped_column(JSONB, default=list)
    extracted_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    maintenance_assumptions: Mapped[dict] = mapped_column(JSONB, default=dict)
    nrc_rc_assumptions: Mapped[dict] = mapped_column(JSONB, default=dict)
    theme_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    style_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    template_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cover_values: Mapped[dict] = mapped_column(JSONB, default=dict)
    calculation_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    project_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    documents = relationship(
        "EstimateDocument",
        back_populates="estimate",
        cascade="all, delete-orphan",
    )
    feature_items = relationship(
        "FeatureItem",
        back_populates="estimate",
        cascade="all, delete-orphan",
    )
    exports = relationship(
        "Export",
        back_populates="estimate",
        cascade="all, delete-orphan",
    )
    actuals = relationship(
        "Actuals",
        back_populates="estimate",
        cascade="all, delete-orphan",
        uselist=False,
    )
    audit_logs = relationship(
        "AuditLog",
        back_populates="estimate",
        cascade="all, delete-orphan",
    )


class EstimateDocument(Base):
    __tablename__ = "estimate_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estimate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estimates.id", ondelete="CASCADE")
    )
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
    estimate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estimates.id", ondelete="CASCADE")
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    hours: Mapped[float] = mapped_column(Numeric(10, 2))
    phase: Mapped[str] = mapped_column(String(50))
    role: Mapped[str] = mapped_column(String(50))
    localizations: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    estimate = relationship("Estimate", back_populates="feature_items")


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estimate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estimates.id", ondelete="CASCADE")
    )
    format: Mapped[str] = mapped_column(String(32))
    storage_path: Mapped[str] = mapped_column(String(1024))
    locale: Mapped[str] = mapped_column(String(2))
    quotation_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(32), nullable=True)
    external_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    manually_edited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    generated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    estimate = relationship("Estimate", back_populates="exports")


class Actuals(Base):
    __tablename__ = "actuals"
    __table_args__ = (UniqueConstraint("estimate_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estimate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estimates.id", ondelete="CASCADE")
    )
    actual_effort_hours: Mapped[float] = mapped_column(Numeric(10, 2))
    actual_duration_days: Mapped[float] = mapped_column(Numeric(10, 2))
    actual_nrc_jpy: Mapped[int] = mapped_column(Integer)
    actual_rc_monthly_jpy: Mapped[int] = mapped_column(Integer)
    variance_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    entered_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    entered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    estimate = relationship("Estimate", back_populates="actuals")
