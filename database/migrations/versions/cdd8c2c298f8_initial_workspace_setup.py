"""initial workspace setup

Revision ID: cdd8c2c298f8
Revises: 
Create Date: 2026-08-09 15:53:25.894155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cdd8c2c298f8'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create profiles table
    op.create_table('profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # Create exams table
    op.create_table('exams',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('is_college', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create subjects table
    op.create_table('subjects',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('exam_id', sa.UUID(), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('normalized_name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('exam_id', 'normalized_name', name='uix_exam_normalized_subject')
    )
    
    # Seed data
    op.execute("""
        INSERT INTO exams (id, name, is_college, created_at)
        VALUES 
            (gen_random_uuid(), 'KCET', false, now()),
            (gen_random_uuid(), 'NEET', false, now()),
            (gen_random_uuid(), 'COMED-K', false, now()),
            (gen_random_uuid(), 'College / University', true, now())
        ON CONFLICT (name) DO NOTHING;
    """)

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('subjects')
    op.drop_table('exams')
    op.drop_table('profiles')
