"""Task model definitions."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, Column, Index
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover
    from .user import User


class TaskState(str, Enum):
    """Task state machine states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_REPLY = "waiting_for_reply"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(SQLModel, table=True):
    """Background task metadata."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    task_type: str = Field(nullable=False, index=True)
    state: str = Field(default="pending", index=True)
    priority: int = Field(default=0, index=True)
    attempts: int = Field(default=0)
    max_attempts: int = Field(default=3)
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
    result: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
    scheduled_for: Optional[datetime] = Field(default=None)
    locked_at: Optional[datetime] = Field(default=None)
    last_attempt_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    last_error: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    user: Optional["User"] = Relationship(back_populates="tasks")

    __table_args__ = (
        Index("ix_task_scheduled_for", "scheduled_for"),
        Index("ix_task_locked_at", "locked_at"),
        Index("ix_task_completed_at", "completed_at"),
    )

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
