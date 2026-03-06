"""Property model for normalised property addresses."""

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import db


class Property(db.Model):
    __tablename__ = "properties"
    __table_args__ = (
        UniqueConstraint("client_id", "address", name="uq_properties_client_address"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    postcode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    client = relationship("Client", back_populates="properties")
    tenants = relationship("Tenant", back_populates="property")
    documents = relationship("Document", back_populates="property")
