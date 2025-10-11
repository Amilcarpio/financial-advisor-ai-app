"""Vector-backed item model definitions."""
from datetime import datetime
from typing import Any, Dict, Optional

from pgvector.sqlalchemy import Vector  # type: ignore[import]
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

DEFAULT_VECTOR_DIMENSION = 1536


class VectorItem(SQLModel, table=True):
    """Embeddable item used for semantic retrieval."""

    id: Optional[int] = Field(default=None, primary_key=True)
    reference_type: str = Field(index=True, nullable=False)
    reference_id: Optional[str] = Field(default=None, index=True)
    embedding: Optional[list[float]] = Field(
        default=None,
        sa_column=Column(Vector(DEFAULT_VECTOR_DIMENSION), nullable=True),
    )
    metadata_json: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
