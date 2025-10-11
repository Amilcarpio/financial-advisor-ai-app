"""User model definitions."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover
    from .contact import Contact
    from .email import Email
    from .memory_rule import MemoryRule
    from .task import Task
    from .vector_item import VectorItem


class User(SQLModel, table=True):
    """Application user and OAuth credentials holder."""

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, nullable=False)
    full_name: Optional[str] = Field(default=None)
    timezone: Optional[str] = Field(default=None)
    google_oauth_tokens: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
    hubspot_oauth_tokens: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
    google_history_id: Optional[str] = Field(default=None, index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    emails: List["Email"] = Relationship(back_populates="user")
    contacts: List["Contact"] = Relationship(back_populates="user")
    vector_items: List["VectorItem"] = Relationship(back_populates="user")
    tasks: List["Task"] = Relationship(back_populates="user")
    memory_rules: List["MemoryRule"] = Relationship(back_populates="user")

    def touch(self) -> None:
        """Update the modification timestamp."""

        self.updated_at = datetime.utcnow()
