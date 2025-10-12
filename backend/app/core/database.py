"""Database engine and helper utilities."""
import logging
from collections.abc import Iterator

from sqlalchemy import text, create_engine
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
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

    Base.metadata.create_all(engine)


# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Iterator[Session]:
    """Provide a managed SQLAlchemy session for FastAPI dependency injection."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
