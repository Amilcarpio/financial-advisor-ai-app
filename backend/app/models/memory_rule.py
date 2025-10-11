"""Memory rule model definitions."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover
    from .user import User


class MemoryRule(SQLModel, table=True):
    """Rule describing how long-term memory should behave."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    rule_text: str = Field(nullable=False)
    is_active: bool = Field(default=True, index=True)
    priority: int = Field(default=0, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_triggered_at: Optional[datetime] = Field(default=None, index=True)

    user: "User" = Relationship(back_populates="memory_rules")

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
