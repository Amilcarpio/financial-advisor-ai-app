"""Add parent_task_id to task table

Revision ID: add_parent_task_id
Revises: add_hubspot_portal_id
Create Date: 2024-01-15 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_parent_task_id'
down_revision = 'add_hubspot_portal_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add parent_task_id column to task table for task hierarchy."""
    op.add_column('task', sa.Column('parent_task_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_task_parent_task_id'), 'task', ['parent_task_id'], unique=False)
    op.create_foreign_key('fk_task_parent_task_id', 'task', 'task', ['parent_task_id'], ['id'])


def downgrade() -> None:
    """Remove parent_task_id column from task table."""
    op.drop_constraint('fk_task_parent_task_id', 'task', type_='foreignkey')
    op.drop_index(op.f('ix_task_parent_task_id'), table_name='task')
    op.drop_column('task', 'parent_task_id')
