"""Email model definitions."""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Email(SQLModel, table=True):
    """Inbound or outbound email metadata."""

    id: Optional[int] = Field(default=None, primary_key=True)
    subject: Optional[str] = None
    body: Optional[str] = None
    sender: Optional[str] = Field(default=None, index=True)
    recipient: Optional[str] = Field(default=None, index=True)
    thread_id: Optional[str] = Field(default=None, index=True)
    received_at: Optional[datetime] = Field(default=None, index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
