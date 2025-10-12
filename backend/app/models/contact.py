"""Contact model definitions."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:  # pragma: no cover
    from .user import User


class Contact(Base):
    """CRM contact synchronized from external systems."""

    __tablename__ = "contact"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    hubspot_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    external_source: Mapped[str] = mapped_column(String, nullable=False, default="hubspot")
    primary_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    secondary_emails: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    first_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lifecycle_stage: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    properties_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship(back_populates="contacts")

    __table_args__ = (
        Index("ix_contact_hubspot_id", "hubspot_id"),
        Index("ix_contact_primary_email", "primary_email"),
        Index("ix_contact_external_source", "external_source"),
        Index("ix_contact_last_synced_at", "last_synced_at"),
    )

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
