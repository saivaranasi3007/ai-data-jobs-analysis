"""
SQLite layer.

Loads the cleaned dataframe into an in-process SQLite database, runs each .sql
file in /sql/, and returns a dict of named result frames. Both `analysis.py`
and the Streamlit dashboard use this so the queries live in exactly one place.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pandas as pd

CLEAN_PATH = "data/ai_jobs_cleaned.csv"
SQL_DIR = "sql"
DB_PATH = "data/jobs.db"
TABLE = "jobs"


def build_database(df: pd.DataFrame | None = None, db_path: str = DB_PATH) -> str:
    """Materialise the jobs table on disk so it can be queried from anywhere."""
    if df is None:
        if not os.path.exists(CLEAN_PATH):
            raise FileNotFoundError(
                f"Missing {CLEAN_PATH}. Run `python analysis.py` first."
            )
        df = pd.read_csv(CLEAN_PATH)

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        df.to_sql(TABLE, conn, if_exists="replace", index=False)
    return db_path


def run_all_queries(db_path: str = DB_PATH) -> dict[str, pd.DataFrame]:
    """Execute every .sql file in /sql/ and return {filename_stem: dataframe}."""
    if not os.path.exists(db_path):
        build_database()

    results: dict[str, pd.DataFrame] = {}
    sql_files = sorted(Path(SQL_DIR).glob("*.sql"))
    with sqlite3.connect(db_path) as conn:
        for path in sql_files:
            sql = path.read_text()
            results[path.stem] = pd.read_sql_query(sql, conn)
    return results


def run_query(name: str, db_path: str = DB_PATH) -> pd.DataFrame:
    """Run a single named query (filename without .sql)."""
    if not os.path.exists(db_path):
        build_database()
    sql_path = Path(SQL_DIR) / f"{name}.sql"
    sql = sql_path.read_text()
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(sql, conn)


if __name__ == "__main__":
    path = build_database()
    print(f"Built {path}")
    print(f"Running {len(list(Path(SQL_DIR).glob('*.sql')))} SQL files...\n")
    results = run_all_queries()
    for name, frame in results.items():
        print("=" * 70)
        print(name)
        print("=" * 70)
        print(frame.to_string(index=False))
        print()
