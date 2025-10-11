"""Database engine and helper utilities."""
import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlmodel import Session, SQLModel, create_engine

from .config import settings


logger = logging.getLogger(__name__)


def _build_engine_url() -> str:
    if not settings.database_url:
        raise ValueError("DATABASE_URL is not configured")
    return settings.database_url


def _create_engine():
    return create_engine(
        _build_engine_url(),
        echo=settings.debug_sql,
        pool_pre_ping=True,
    )


def _should_create_pgvector_extension() -> bool:
    return settings.auto_create_pgvector_extension and engine.url.get_backend_name() == "postgresql"


engine = _create_engine()


def create_db_and_tables() -> None:
    """Create database tables and ensure the pgvector extension exists when requested."""

    if _should_create_pgvector_extension():
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except ProgrammingError as exc:
            # The database user may not have permission to install extensions.
            # Log and continue so the application can still start.
            warning = (
                "Could not create pgvector extension automatically. "
                "Ensure it exists manually if vector search is required."
            )
            logger.warning("%s (%s)", warning, exc)

    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session() -> Iterator[Session]:
    """Provide a managed SQLModel session."""

    with Session(engine) as session:
        yield session
