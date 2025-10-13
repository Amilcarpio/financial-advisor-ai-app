"""Task model definitions."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:  # pragma: no cover
    from .user import User


class TaskState(str, Enum):
    """Task state machine states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_REPLY = "waiting_for_reply"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(Base):
    """Background task metadata."""

    __tablename__ = "task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("user.id"), nullable=True, index=True)
    parent_task_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("task.id"), nullable=True, index=True
    )
    task_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    state: Mapped[str] = mapped_column(String, nullable=False, default="pending", index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship(back_populates="tasks")
    
    # Self-referential relationship for task hierarchy
    parent_task: Mapped[Optional["Task"]] = relationship(
        "Task", 
        remote_side=[id],
        foreign_keys=[parent_task_id],
        backref="child_tasks"
    )

    __table_args__ = (
        Index("ix_task_scheduled_for", "scheduled_for"),
        Index("ix_task_locked_at", "locked_at"),
        Index("ix_task_completed_at", "completed_at"),
    )

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
