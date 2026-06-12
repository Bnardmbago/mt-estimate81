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
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_locale: Mapped[str] = mapped_column(String(2), default="ja")
    preferred_currency: Mapped[str] = mapped_column(String(3), default="JPY")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def default_client_name(self) -> str:
        if self.company_name and self.company_name.strip():
            return self.company_name.strip()
        if self.display_name and self.display_name.strip():
            return self.display_name.strip()
        return self.email
