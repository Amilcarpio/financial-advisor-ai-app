"""Memory rule model definitions."""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class MemoryRule(SQLModel, table=True):
    """Rule describing how long-term memory should behave."""

    id: Optional[int] = Field(default=None, primary_key=True)
    rule_text: str = Field(nullable=False)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
