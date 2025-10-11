"""Email model definitions."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, Column, Index, String
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover
    from .user import User


class Email(SQLModel, table=True):
    """Inbound or outbound email metadata."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, nullable=False)
    gmail_id: str = Field(sa_column=Column(String(255), unique=True, nullable=False))
    thread_id: Optional[str] = Field(default=None)
    history_id: Optional[str] = Field(default=None)
    subject: Optional[str] = Field(default=None)
    snippet: Optional[str] = Field(default=None)
    body_plain: Optional[str] = Field(default=None)
    body_html: Optional[str] = Field(default=None)
    sender: Optional[str] = Field(default=None)
    reply_to: Optional[str] = Field(default=None)
    to_recipients: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=list),
    )
    cc_recipients: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=list),
    )
    bcc_recipients: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=list),
    )
    labels: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=list),
    )
    headers_json: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
    direction: str = Field(default="inbound")
    is_read: bool = Field(default=True)
    received_at: Optional[datetime] = Field(default=None)
    sent_at: Optional[datetime] = Field(default=None)
    external_source: Optional[str] = Field(default="gmail")
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    user: "User" = Relationship(back_populates="emails")

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
