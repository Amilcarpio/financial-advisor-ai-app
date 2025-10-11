"""Contact model definitions."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, Column, Index, String
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover
    from .user import User


class Contact(SQLModel, table=True):
    """CRM contact synchronized from external systems."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    hubspot_id: Optional[str] = Field(
        default=None,
        sa_column=Column(String(255), unique=True, nullable=True),
    )
    external_source: str = Field(default="hubspot")
    primary_email: Optional[str] = Field(default=None)
    secondary_emails: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=list),
    )
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    company: Optional[str] = Field(default=None)
    phone_number: Optional[str] = Field(default=None)
    lifecycle_stage: Optional[str] = Field(default=None)
    owner_id: Optional[int] = Field(default=None)
    properties_json: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
    last_synced_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    user: "User" = Relationship(back_populates="contacts")

    __table_args__ = (
        Index("ix_contact_hubspot_id", "hubspot_id"),
        Index("ix_contact_primary_email", "primary_email"),
        Index("ix_contact_external_source", "external_source"),
        Index("ix_contact_last_synced_at", "last_synced_at"),
    )

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
