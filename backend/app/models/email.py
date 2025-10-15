"""Email model definitions."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:  # pragma: no cover
    from .user import User


class Email(Base):
    """Inbound or outbound email metadata."""

    __tablename__ = "email"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    gmail_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    thread_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    history_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_plain: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sender: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reply_to: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    to_recipients: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    cc_recipients: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    bcc_recipients: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    labels: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    headers_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    direction: Mapped[str] = mapped_column(String, nullable=False, default="inbound")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    external_source: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="gmail")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship(back_populates="emails")

    __table_args__ = (
        Index("ix_email_thread_id", "thread_id"),
        Index("ix_email_history_id", "history_id"),
        Index("ix_email_sender", "sender"),
        Index("ix_email_direction", "direction"),
        Index("ix_email_is_read", "is_read"),
        Index("ix_email_received_at", "received_at"),
        Index("ix_email_sent_at", "sent_at"),
        Index("ix_email_external_source", "external_source"),
    )

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
