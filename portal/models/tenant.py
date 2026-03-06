"""Tenant model for tenancy-oriented filtering and compliance context."""

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import db


class Tenant(db.Model):
    __tablename__ = "tenants"
    __table_args__ = (
        UniqueConstraint("client_id", "property_id", "full_name", name="uq_tenants_client_property_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tenancy_start: Mapped[Date | None] = mapped_column(Date, nullable=True)
    tenancy_end: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    client = relationship("Client", back_populates="tenants")
    property = relationship("Property", back_populates="tenants")
