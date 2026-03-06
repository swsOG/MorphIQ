"""Document type model, mapped to template-like schema definitions."""

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import db


class DocumentType(db.Model):
    __tablename__ = "document_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_expiry: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expiry_field_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    documents = relationship("Document", back_populates="document_type")
