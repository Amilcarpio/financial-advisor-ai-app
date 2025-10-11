"""Vector-backed item model definitions."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

from pgvector.sqlalchemy import Vector  # type: ignore[import]
from sqlalchemy import Column, Index, JSON, String
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover
    from .user import User

DEFAULT_VECTOR_DIMENSION = 1536


class VectorItem(SQLModel, table=True):
    """Embeddable item used for semantic retrieval."""

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True, index=True)
    user_id: int = Field(foreign_key="user.id", index=True, nullable=False)
    source_type: str = Field(nullable=False, index=True)
    source_id: Optional[str] = Field(default=None)
    chunk_index: Optional[int] = Field(default=None)
    chunk_count: Optional[int] = Field(default=None)
    text: str = Field(nullable=False)
    tokens: Optional[int] = Field(default=None)
    embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(Vector(DEFAULT_VECTOR_DIMENSION), nullable=True),
    )
    metadata_json: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    user: "User" = Relationship(back_populates="vector_items")

    __table_args__ = (
        Index("ix_vector_item_source", "source_type", "source_id"),
        Index("ix_vector_item_created_at", "created_at"),
    )

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
