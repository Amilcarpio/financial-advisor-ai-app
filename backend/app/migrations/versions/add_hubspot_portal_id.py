"""Add hubspot_portal_id to user table

Revision ID: add_hubspot_portal_id
Revises: 08c8e8cb47ad
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_hubspot_portal_id'
down_revision = '08c8e8cb47ad'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add hubspot_portal_id column to user table."""
    op.add_column('user', sa.Column('hubspot_portal_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_user_hubspot_portal_id'), 'user', ['hubspot_portal_id'], unique=False)


def downgrade() -> None:
    """Remove hubspot_portal_id column from user table."""
    op.drop_index(op.f('ix_user_hubspot_portal_id'), table_name='user')
    op.drop_column('user', 'hubspot_portal_id')
