"""
database.py — How we talk to the database.

One engine + one session factory for the whole app.
Switching from SQLite (dev) to Postgres (prod) is just changing DATABASE_URL.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from . import config


class Base(DeclarativeBase):
    """Every database model in models.py inherits from this one class.
    SQLAlchemy reads the tables from here when we create them."""


# ---------------------------------------------------------------------------
# Engine + Session
# ---------------------------------------------------------------------------

# SQLite doesn't need thread checks (we're single-process in dev).
# connect_args={} is a no-op for Postgres, so it's safe for both.
engine = create_engine(config.DB_URL, connect_args={"check_same_thread": False})

# A "session factory" = a recipe that hands us a fresh database session each time.
# Sessions are short-lived: open one per request, close it when done.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    """FastAPI dependency: gives each request its own database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # always free the connection, even if the request errored


def init_db() -> None:
    """Create all tables that don't exist yet. Run once at startup."""
    from . import models  # imported here so tables are registered before create_all

    Base.metadata.create_all(bind=engine)
