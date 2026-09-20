import csv
import sqlite3
from pathlib import Path
from db import DB_PATH, get_connection

CSV_PATH = Path(__file__).parent / "cell-count.csv"

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell" ,"monocyte"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS subjects (
    subject_id  TEXT PRIMARY KEY,
    project     TEXT NOT NULL,
    condition   TEXT NOT NULL,
    age         INTEGER,
    sex         TEXT,
    treatment   TEXT,
    response    TEXT
);

CREATE TABLE IF NOT EXISTS samples (
    sample_id       TEXT PRIMARY KEY,
    subject_id      TEXT NOT NULL,
    sample_type     TEXT NOT NULL,
    time_from_treatment_start INTEGER,
    FOREIGN KEY (subject_id) REFERENCES subjects (subject_id)
);

CREATE TABLE IF NOT EXISTS cell_counts (
    sample_id   TEXT NOT NULL,
    population  TEXT NOT NULL,
    count       INTEGER NOT NULL,
    PRIMARY KEY (sample_id, population),
    FOREIGN KEY (sample_id) REFERENCES samples (sample_id)
);
"""


def init_db(conn: sqlite3.Connection) -> None:
    """Create the database schema"""
    conn.executescript(SCHEMA)


def load_csv(conn: sqlite3.Connection, csv_path: Path) -> None:
    """Load the CSV into the schema, assuming schema already exists."""
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute(
                """
                INSERT OR IGNORE INTO subjects
                    (subject_id, project, condition, age, sex, treatment, response)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (row["subject"], row["project"], row["condition"], int(row["age"]), row["sex"], row["treatment"], row["response"])
            )
            conn.execute(
                """
                INSERT INTO samples (sample_id, subject_id, sample_type, time_from_treatment_start)
                VALUES (?, ?, ?, ?)
                """,
                (row["sample"], row["subject"], row["sample_type"], int(row["time_from_treatment_start"]))
            )
            for population in POPULATIONS:
                conn.execute(
                    """
                    INSERT INTO cell_counts (sample_id, population, count)
                    VALUES (?, ?, ?)
                    """,
                    (row["sample"], population, int(row[population]))
                )


def main() -> None:
    """Delete any existing database, then rebuild it from the CSV."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    with get_connection() as conn:
        init_db(conn)
        load_csv(conn, CSV_PATH)


if __name__ == "__main__":
    main()