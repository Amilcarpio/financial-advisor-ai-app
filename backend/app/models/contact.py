"""Contact model definitions."""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Contact(SQLModel, table=True):
    """CRM contact synchronized from external systems."""

    id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = Field(default=None, index=True)
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    phone_number: Optional[str] = Field(default=None)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
