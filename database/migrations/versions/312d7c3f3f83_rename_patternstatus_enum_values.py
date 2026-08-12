"""Rename PatternStatus enum values

Revision ID: 312d7c3f3f83
Revises: 96ecfb2cc896
Create Date: 2026-08-11 18:55:42.188522

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '312d7c3f3f83'
down_revision: Union[str, Sequence[str], None] = '96ecfb2cc896'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename ANALYZED to ACTIVE
    op.execute("ALTER TYPE patternstatus RENAME VALUE 'ANALYZED' TO 'ACTIVE'")
    # Rename PROCESSING to ANALYZING
    op.execute("ALTER TYPE patternstatus RENAME VALUE 'PROCESSING' TO 'ANALYZING'")


def downgrade() -> None:
    # Reverse renaming
    op.execute("ALTER TYPE patternstatus RENAME VALUE 'ACTIVE' TO 'ANALYZED'")
    op.execute("ALTER TYPE patternstatus RENAME VALUE 'ANALYZING' TO 'PROCESSING'")
