"""Vector-backed item model definitions."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

from pgvector.sqlalchemy import Vector  # type: ignore[import]
from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:  # pragma: no cover
    from .user import User

DEFAULT_VECTOR_DIMENSION = 1536


class VectorItem(Base):
    """Embeddable item used for semantic retrieval."""

    __tablename__ = "vectoritem"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    chunk_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(DEFAULT_VECTOR_DIMENSION), nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship(back_populates="vector_items")

    __table_args__ = (
        Index("ix_vector_item_source", "source_type", "source_id"),
        Index("ix_vector_item_created_at", "created_at"),
    )

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
