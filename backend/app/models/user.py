"""User model definitions."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:  # pragma: no cover
    from .contact import Contact
    from .email import Email
    from .memory_rule import MemoryRule
    from .task import Task
    from .vector_item import VectorItem


class User(Base):
    """Application user and OAuth credentials holder."""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    google_oauth_tokens: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    hubspot_oauth_tokens: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    hubspot_portal_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )
    google_history_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    calendar_channel_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    calendar_resource_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    calendar_watch_expiration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)  # Unix timestamp (ms)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships with proper Mapped types
    emails: Mapped[List["Email"]] = relationship(back_populates="user")
    contacts: Mapped[List["Contact"]] = relationship(back_populates="user")
    vector_items: Mapped[List["VectorItem"]] = relationship(back_populates="user")
    tasks: Mapped[List["Task"]] = relationship(back_populates="user")
    memory_rules: Mapped[List["MemoryRule"]] = relationship(back_populates="user")

    def touch(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = datetime.utcnow()
