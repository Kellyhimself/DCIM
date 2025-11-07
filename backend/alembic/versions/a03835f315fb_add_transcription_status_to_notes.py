"""add_transcription_status_to_notes

Revision ID: a03835f315fb
Revises: d8850e9ae31a
Create Date: 2025-11-07 10:15:23.768392

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a03835f315fb'
down_revision = 'd8850e9ae31a'
branch_labels = None
depends_on = None


def upgrade() -> None:
	# Add transcription_status column to notes table
	op.add_column('notes', sa.Column('transcription_status', sa.String(length=50), nullable=False, server_default='pending'))


def downgrade() -> None:
	# Remove transcription_status column from notes table
	op.drop_column('notes', 'transcription_status')
