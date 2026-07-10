from datetime import datetime

from datetime import date

from sqlalchemy import Boolean, BigInteger, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SystemConfig(Base):
    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    ai_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    openai_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    anthropic_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    smtp_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_from: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_use_tls: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    estimate_discount_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimate_markup_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    quotation_special_notes_title_ja: Mapped[str | None] = mapped_column(Text, nullable=True)
    quotation_special_notes_title_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    quotation_special_notes_body_ja: Mapped[str | None] = mapped_column(Text, nullable=True)
    quotation_special_notes_body_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    quotation_invoice_registration_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quotation_contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quotation_company_postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quotation_company_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    quotation_company_tel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quotation_company_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quotation_bank_details_ja: Mapped[str | None] = mapped_column(Text, nullable=True)
    quotation_bank_details_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    quotation_logo_storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    registration_number_sequence: Mapped[int] = mapped_column(BigInteger, default=9010001234561)
    quotation_number_prefix: Mapped[str] = mapped_column(String(10), default="BAI")
    quotation_number_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    quotation_number_sequence: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
