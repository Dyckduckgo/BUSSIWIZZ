"""
Database Engine and Session Management (SQLite)
Provides:
- Thread-safe SQLite engine with WAL mode and foreign key enforcement
- SessionLocal factory and context managers
- Automatic initialization and migration logic for fresh installations
"""

import os
from pathlib import Path
from typing import Generator, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.engine import Engine

# Default SQLite database path in user-writable application-data directory
try:
    from config.app_config import get_db_path
    DEFAULT_DB_PATH = get_db_path()
except Exception:
    DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent / "data"
    DEFAULT_DB_PATH = DEFAULT_DB_DIR / "stock_research.db"

DEFAULT_DB_DIR = DEFAULT_DB_PATH.parent
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

# Base class for all SQLAlchemy declarative models
Base = declarative_base()

_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker] = None


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforces SQLite foreign keys and activates WAL mode for concurrent reads."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    finally:
        cursor.close()


def get_engine(db_url: Optional[str] = None) -> Engine:
    """Returns or creates the singleton SQLAlchemy Engine."""
    global _engine
    url = db_url or DATABASE_URL

    if _engine is None or db_url is not None:
        if url.startswith("sqlite"):
            # Ensure parent directory exists for file-based SQLite
            if "///" in url and not url.startswith("sqlite:///:memory:"):
                db_file_path = url.split("///", 1)[1]
                Path(db_file_path).parent.mkdir(parents=True, exist_ok=True)

            engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
                echo=False,
                future=True,
            )
        else:
            engine = create_engine(url, echo=False, future=True)

        if db_url is None:
            _engine = engine
        return engine

    return _engine


def get_session_factory(engine: Optional[Engine] = None) -> sessionmaker:
    """Returns or creates the sessionmaker factory."""
    global _SessionFactory
    eng = engine or get_engine()
    if _SessionFactory is None or engine is not None:
        factory = sessionmaker(autocommit=False, autoflush=False, bind=eng)
        if engine is None:
            _SessionFactory = factory
        return factory
    return _SessionFactory


def init_db(engine: Optional[Engine] = None) -> None:
    """
    Initializes database schema and automatically applies lightweight migrations.
    Creates all tables declared in database.models if they do not exist.
    Detects and adds missing columns to existing SQLite tables.
    Safe to run repeatedly on fresh or existing installations.
    """
    from database import models  # Ensure all model classes are imported and registered

    target_engine = engine or get_engine()
    Base.metadata.create_all(bind=target_engine)

    # Automatic schema migration for existing SQLite databases
    try:
        with target_engine.connect() as conn:
            for table_name, table in Base.metadata.tables.items():
                try:
                    res = conn.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
                    existing_cols = {row[1] for row in res}
                    for col in table.columns:
                        if col.name not in existing_cols:
                            col_type = col.type.compile(target_engine.dialect)
                            conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}")
                            conn.commit()
                except Exception:
                    pass
    except Exception:
        pass


def reset_db(engine: Optional[Engine] = None) -> None:
    """Drops and recreates all tables (primarily for test suite isolation)."""
    target_engine = engine or get_engine()
    Base.metadata.drop_all(bind=target_engine)
    Base.metadata.create_all(bind=target_engine)


@contextmanager
def get_db_session(engine: Optional[Engine] = None) -> Generator[Session, None, None]:
    """
    Transactional context manager for database sessions.
    Automatically commits on success or rolls back on exception.
    """
    factory = get_session_factory(engine)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
