"""notes media

Revision ID: 1962325355ec
Revises: 0001_initial
Create Date: 2025-10-30 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1962325355ec'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
	# Teams
	op.create_table(
		'teams',
		sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column('name', sa.String(length=255), nullable=False),
		sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
		sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
		sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
		sa.PrimaryKeyConstraint('id')
	)
	op.create_index('ix_teams_owner_id', 'teams', ['owner_id'], unique=False)

	op.create_table(
		'team_members',
		sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column('role', sa.String(length=50), nullable=False),
		sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
		sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
		sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
		sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
		sa.PrimaryKeyConstraint('id')
	)
	op.create_index('ix_team_members_team_id', 'team_members', ['team_id'], unique=False)
	op.create_index('ix_team_members_user_id', 'team_members', ['user_id'], unique=False)

	op.create_table(
		'team_invites',
		sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column('email', sa.String(length=255), nullable=False),
		sa.Column('token', sa.String(length=255), nullable=False),
		sa.Column('accepted', sa.Boolean(), nullable=False),
		sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
		sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
		sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
		sa.PrimaryKeyConstraint('id')
	)
	op.create_index('ix_team_invites_team_id', 'team_invites', ['team_id'], unique=False)
	op.create_index('ix_team_invites_email', 'team_invites', ['email'], unique=False)
	op.create_index('ix_team_invites_token', 'team_invites', ['token'], unique=True)

	# Notes/Media as before
	op.create_table('notes',
		sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
		sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=True),
		sa.Column('assignee_id', postgresql.UUID(as_uuid=True), nullable=True),
		sa.Column('text', sa.String(), nullable=True),
		sa.Column('status', sa.String(length=50), nullable=False),
		sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
		sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
		sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ondelete='SET NULL'),
		sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='SET NULL'),
		sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='SET NULL'),
		sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
		sa.PrimaryKeyConstraint('id')
	)
	op.create_index('ix_notes_owner_id', 'notes', ['owner_id'], unique=False)
	op.create_index('ix_notes_assignee_id', 'notes', ['assignee_id'], unique=False)

	op.create_table('media',
		sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column('note_id', postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column('type', sa.String(length=20), nullable=False),
		sa.Column('key', sa.String(length=512), nullable=False),
		sa.Column('content_type', sa.String(length=100), nullable=True),
		sa.Column('uploaded', sa.Boolean(), nullable=False),
		sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
		sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
		sa.ForeignKeyConstraint(['note_id'], ['notes.id'], ondelete='CASCADE'),
		sa.PrimaryKeyConstraint('id')
	)
	op.create_index('ix_media_note_id', 'media', ['note_id'], unique=False)
	# The following were detected by autogenerate; ensure they match your intent
	op.alter_column('clients', 'created_at', existing_type=sa.DateTime(timezone=True), nullable=False)
	op.alter_column('clients', 'updated_at', existing_type=sa.DateTime(timezone=True), nullable=False)
	op.alter_column('jobs', 'created_at', existing_type=sa.DateTime(timezone=True), nullable=False)
	op.alter_column('jobs', 'updated_at', existing_type=sa.DateTime(timezone=True), nullable=False)
	op.alter_column('users', 'created_at', existing_type=sa.DateTime(timezone=True), nullable=False)
	op.alter_column('users', 'updated_at', existing_type=sa.DateTime(timezone=True), nullable=False)


def downgrade() -> None:
	op.drop_index('ix_media_note_id', table_name='media')
	op.drop_table('media')
	op.drop_index('ix_notes_assignee_id', table_name='notes')
	op.drop_index('ix_notes_owner_id', table_name='notes')
	op.drop_table('notes')
	op.drop_index('ix_team_invites_token', table_name='team_invites')
	op.drop_index('ix_team_invites_email', table_name='team_invites')
	op.drop_index('ix_team_invites_team_id', table_name='team_invites')
	op.drop_table('team_invites')
	op.drop_index('ix_team_members_user_id', table_name='team_members')
	op.drop_index('ix_team_members_team_id', table_name='team_members')
	op.drop_table('team_members')
	op.drop_index('ix_teams_owner_id', table_name='teams')
	op.drop_table('teams')
