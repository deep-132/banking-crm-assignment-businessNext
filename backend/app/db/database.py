import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import get_settings

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _resolve_db_path() -> Path:
    settings = get_settings()
    path = Path(settings.database_path)
    if not path.is_absolute():
        # resolve relative to backend/ (parent of app/)
        backend_root = Path(__file__).resolve().parents[2]
        path = backend_root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_resolve_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection_scope():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_schema() -> None:
    schema_sql = _SCHEMA_PATH.read_text()
    with connection_scope() as conn:
        conn.executescript(schema_sql)


def reset_database() -> None:
    """Drop and recreate all tables — used by the admin reseed endpoint."""
    tables = [
        "interactions",
        "products_held",
        "transactions",
        "accounts",
        "loan_offers",
        "customers",
    ]
    with connection_scope() as conn:
        for table in tables:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
    init_schema()
