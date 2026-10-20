"""add_work_item_key_sequence

Revision ID: 3601d4157959
Revises: 1c1d1208dcd7
Create Date: 2026-10-21

"""
from alembic import op

revision = '3601d4157959'
down_revision = '1c1d1208dcd7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create a sequence for work item keys - this ensures atomic, gap-free key generation
    op.execute("CREATE SEQUENCE IF NOT EXISTS work_item_key_seq START WITH 1 INCREMENT BY 1 NO MAXVALUE CACHE 1")


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS work_item_key_seq")
