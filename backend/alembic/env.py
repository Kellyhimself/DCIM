from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure project root (parent of 'backend') is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # backend/alembic
BACKEND_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir))  # backend
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, os.pardir))
for path in (PROJECT_ROOT,):
	if path not in sys.path:
		sys.path.insert(0, path)

from backend.app.settings import settings  # type: ignore
from backend.app.db import Base  # type: ignore
import backend.app.models  # noqa: F401 ensure models imported

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
	fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support

target_metadata = Base.metadata

# set sqlalchemy.url from settings
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
	url = config.get_main_option("sqlalchemy.url")
	context.configure(
		url=url,
		target_metadata=target_metadata,
		literal_binds=True,
		dialect_opts={"paramstyle": "named"},
	)

	with context.begin_transaction():
		context.run_migrations()


def run_migrations_online() -> None:
	connectable = engine_from_config(
		config.get_section(config.config_ini_section) or {},
		prefix="sqlalchemy.",
		poolclass=pool.NullPool,
	)

	with connectable.connect() as connection:
		context.configure(connection=connection, target_metadata=target_metadata)

		with context.begin_transaction():
			context.run_migrations()


if context.is_offline_mode():
	run_migrations_offline()
else:
	run_migrations_online()
