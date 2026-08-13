"""Database connection settings for the project's Postgres data platform.

Everything is read from environment variables with sensible local defaults, so
the same code works in three places without edits:

  - from Windows / the venv  : localhost:5435 (the port docker-compose publishes)
  - from inside an Airflow container : postgres:5432 (the compose service name)
  - from a marker's machine  : whatever they set in the environment

Defaults match docker-compose.yml. Nothing secret lives here: this is a local
analytics database created for an academic project, and the confidential source
data is never committed.
"""

import os

PG_HOST = os.environ.get("PP_PG_HOST", "localhost")
PG_PORT = int(os.environ.get("PP_PG_PORT", "5435"))
PG_DATABASE = os.environ.get("PP_PG_DATABASE", "product_placement")
PG_USER = os.environ.get("PP_PG_USER", "postgres")
PG_PASSWORD = os.environ.get("PP_PG_PASSWORD", "postgres")


def connection_kwargs():
    """Keyword arguments for psycopg2.connect()."""
    return {
        "host": PG_HOST,
        "port": PG_PORT,
        "dbname": PG_DATABASE,
        "user": PG_USER,
        "password": PG_PASSWORD,
    }


def sqlalchemy_url():
    """SQLAlchemy / pandas connection string for the same database."""
    return (
        f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}"
        f"@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"
    )


def describe():
    """Human readable target, safe to print (no password)."""
    return f"{PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"
