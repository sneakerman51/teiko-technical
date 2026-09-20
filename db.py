import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "cell_count.db"

@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Connect and commit on success and always close."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally: 
        conn.close()