"""initial

Revision ID: 0001_initial
Revises: 
Create Date: 2025-10-30 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table(
		'users',
		sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
		sa.Column('email', sa.String(length=255), nullable=False, unique=True),
		sa.Column('full_name', sa.String(length=255), nullable=True),
		sa.Column('password_hash', sa.String(length=255), nullable=False),
		sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
		sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
	)
	op.create_index('ix_users_email', 'users', ['email'], unique=True)

	op.create_table(
		'clients',
		sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
		sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False),
		sa.Column('name', sa.String(length=255), nullable=False),
		sa.Column('phone', sa.String(length=50), nullable=True),
		sa.Column('location', sa.String(length=255), nullable=True),
		sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
		sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
	)

	op.create_table(
		'jobs',
		sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
		sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False),
		sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), index=True, nullable=False),
		sa.Column('site', sa.String(length=255), nullable=True),
		sa.Column('status', sa.String(length=50), nullable=False),
		sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
		sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
	)


def downgrade() -> None:
	op.drop_table('jobs')
	op.drop_table('clients')
	op.drop_index('ix_users_email', table_name='users')
	op.drop_table('users')
