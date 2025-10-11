import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool, String
from sqlmodel import SQLModel

# Ensure application modules are importable
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402
from app.models import *  # noqa: F403,F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

if settings.database_url:
    config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = SQLModel.metadata


def render_item(type_, obj, autogen_context):
    """Render SQLModel AutoString as standard SQLAlchemy String."""
    if type_ == "type" and hasattr(obj, "__class__"):
        # Convert AutoString to standard String
        if obj.__class__.__name__ == "AutoString":
            return "sa.String()"
    return False


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,
            render_item=render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
