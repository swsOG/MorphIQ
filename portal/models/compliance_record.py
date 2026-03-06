"""Compliance events derived from document fields with expiry-style dates."""

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import db


class ComplianceRecord(db.Model):
    __tablename__ = "compliance_records"
    __table_args__ = (
        UniqueConstraint("document_id", "record_type", name="uq_compliance_records_doc_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    record_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    expiry_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="upcoming", index=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    document = relationship("Document", back_populates="compliance_records")
