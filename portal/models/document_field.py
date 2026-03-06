"""Per-document extracted fields from review.json."""

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import db


class DocumentField(db.Model):
    __tablename__ = "document_fields"
    __table_args__ = (
        UniqueConstraint("document_id", "field_key", name="uq_document_fields_document_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    field_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    field_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    field_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="review_json")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    document = relationship("Document", back_populates="fields")
