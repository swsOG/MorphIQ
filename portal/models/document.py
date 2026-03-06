"""Document model linked to existing DOC-XXXXX IDs and review/export metadata."""

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import db


class Document(db.Model):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("client_id", "source_doc_id", name="uq_documents_client_source_doc_id"),
        CheckConstraint("source_doc_id ~ '^DOC-[0-9]{5}$'", name="source_doc_id_format"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True)
    document_type_id: Mapped[int | None] = mapped_column(ForeignKey("document_types.id", ondelete="SET NULL"), nullable=True, index=True)
    source_doc_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    doc_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text_search: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    quality_score: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reviewed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scanned_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exported_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    imported_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    batch_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    client = relationship("Client", back_populates="documents")
    property = relationship("Property", back_populates="documents")
    document_type = relationship("DocumentType", back_populates="documents")
    fields = relationship("DocumentField", back_populates="document", cascade="all, delete-orphan")
    compliance_records = relationship("ComplianceRecord", back_populates="document", cascade="all, delete-orphan")
