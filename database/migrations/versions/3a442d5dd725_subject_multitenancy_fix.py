"""subject_multitenancy_fix

Revision ID: 3a442d5dd725
Revises: e01c5bae638d
Create Date: 2026-08-13 11:36:32.308894

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a442d5dd725'
down_revision: Union[str, Sequence[str], None] = 'e01c5bae638d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('uix_exam_normalized_subject', 'subjects', type_='unique')
    op.create_unique_constraint('uix_exam_owner_normalized_subject', 'subjects', ['exam_id', 'created_by', 'normalized_name'])

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uix_exam_owner_normalized_subject', 'subjects', type_='unique')
    op.create_unique_constraint('uix_exam_normalized_subject', 'subjects', ['exam_id', 'normalized_name'])
