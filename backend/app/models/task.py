"""Task model definitions."""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Task(SQLModel, table=True):
    """Background task metadata."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, index=True)
    status: str = Field(default="pending", index=True)
    payload: Optional[str] = Field(default=None)
    scheduled_for: Optional[datetime] = Field(default=None, index=True)
    completed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
