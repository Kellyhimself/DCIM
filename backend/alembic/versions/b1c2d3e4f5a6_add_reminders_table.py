"""add_reminders_table

Revision ID: b1c2d3e4f5a6
Revises: a03835f315fb
Create Date: 2025-11-07 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a6'
down_revision = 'a03835f315fb'
branch_labels = None
depends_on = None


def upgrade() -> None:
	# Create reminders table
	op.create_table(
		'reminders',
		sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
		sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column('note_id', postgresql.UUID(as_uuid=True), nullable=True),
		sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=True),
		sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
		sa.Column('text', sa.Text(), nullable=False),
		sa.Column('type', sa.String(length=50), nullable=False, server_default='follow_up'),
		sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
		sa.Column('due_date_text', sa.String(length=255), nullable=True),
		sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
		sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
		sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
		sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
	)
	
	# Create indexes
	op.create_index('ix_reminders_owner_id', 'reminders', ['owner_id'])
	op.create_index('ix_reminders_note_id', 'reminders', ['note_id'])
	op.create_index('ix_reminders_job_id', 'reminders', ['job_id'])
	op.create_index('ix_reminders_client_id', 'reminders', ['client_id'])
	op.create_index('ix_reminders_due_date', 'reminders', ['due_date'])
	
	# Create foreign keys
	op.create_foreign_key(
		'fk_reminders_owner_id_users',
		'reminders', 'users',
		['owner_id'], ['id'],
		ondelete='CASCADE'
	)
	op.create_foreign_key(
		'fk_reminders_note_id_notes',
		'reminders', 'notes',
		['note_id'], ['id'],
		ondelete='SET NULL'
	)
	op.create_foreign_key(
		'fk_reminders_job_id_jobs',
		'reminders', 'jobs',
		['job_id'], ['id'],
		ondelete='SET NULL'
	)
	op.create_foreign_key(
		'fk_reminders_client_id_clients',
		'reminders', 'clients',
		['client_id'], ['id'],
		ondelete='SET NULL'
	)


def downgrade() -> None:
	# Drop foreign keys
	op.drop_constraint('fk_reminders_client_id_clients', 'reminders', type_='foreignkey')
	op.drop_constraint('fk_reminders_job_id_jobs', 'reminders', type_='foreignkey')
	op.drop_constraint('fk_reminders_note_id_notes', 'reminders', type_='foreignkey')
	op.drop_constraint('fk_reminders_owner_id_users', 'reminders', type_='foreignkey')
	
	# Drop indexes
	op.drop_index('ix_reminders_due_date', table_name='reminders')
	op.drop_index('ix_reminders_client_id', table_name='reminders')
	op.drop_index('ix_reminders_job_id', table_name='reminders')
	op.drop_index('ix_reminders_note_id', table_name='reminders')
	op.drop_index('ix_reminders_owner_id', table_name='reminders')
	
	# Drop table
	op.drop_table('reminders')

