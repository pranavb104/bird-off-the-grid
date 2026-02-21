"""SQLite database operations for BirdNET detections."""

import sqlite3
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    common_name TEXT NOT NULL,
    scientific_name TEXT NOT NULL,
    confidence REAL NOT NULL,
    file_path TEXT NOT NULL,
    audio_path TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_date ON detections(date);
CREATE INDEX IF NOT EXISTS idx_species ON detections(scientific_name);
"""

MAX_RETRIES = 3
RETRY_DELAY = 0.5


def _get_db_path(data_dir: str) -> str:
    return str(Path(data_dir) / "birds.db")


def _execute_with_retry(db_path: str, func, *args):
    """Execute a database function with retry logic for busy/locked errors."""
    for attempt in range(MAX_RETRIES):
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            try:
                result = func(conn, *args)
                conn.commit()
                return result
            finally:
                conn.close()
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
            if attempt < MAX_RETRIES - 1:
                logger.warning("DB retry %d/%d: %s", attempt + 1, MAX_RETRIES, e)
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise


def init_db(data_dir: str):
    """Initialize the database and create tables if needed."""
    db_path = _get_db_path(data_dir)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.close()
    logger.info("Database initialized at %s", db_path)


def insert_detection(data_dir: str, date: str, time_str: str, common_name: str,
                     scientific_name: str, confidence: float, file_path: str,
                     audio_path: str):
    """Insert a new detection record."""
    def _insert(conn, *args):
        conn.execute(
            "INSERT INTO detections (date, time, common_name, scientific_name, "
            "confidence, file_path, audio_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
            args
        )

    _execute_with_retry(
        _get_db_path(data_dir), _insert,
        date, time_str, common_name, scientific_name, confidence,
        file_path, audio_path
    )
    logger.info("Saved detection: %s (%.2f)", common_name, confidence)


def get_recent(data_dir: str, limit: int = 10) -> list[dict]:
    """Get the most recent N detections."""
    def _query(conn):
        rows = conn.execute(
            "SELECT * FROM detections ORDER BY date DESC, time DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    return _execute_with_retry(_get_db_path(data_dir), _query)


def get_by_hour(data_dir: str, date: str = None) -> list[dict]:
    """Get detections grouped by hour for a given date (default: today)."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    def _query(conn):
        rows = conn.execute(
            "SELECT substr(time, 1, 2) as hour, COUNT(*) as count "
            "FROM detections WHERE date = ? GROUP BY hour ORDER BY hour",
            (date,)
        ).fetchall()
        return [dict(r) for r in rows]

    return _execute_with_retry(_get_db_path(data_dir), _query)


def get_overview(data_dir: str) -> dict:
    """Get summary statistics."""
    def _query(conn):
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        total = conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
        unique_species = conn.execute(
            "SELECT COUNT(DISTINCT scientific_name) FROM detections"
        ).fetchone()[0]
        today_count = conn.execute(
            "SELECT COUNT(*) FROM detections WHERE date = ?", (today,)
        ).fetchone()[0]
        week_count = conn.execute(
            "SELECT COUNT(*) FROM detections WHERE date >= ?", (week_ago,)
        ).fetchone()[0]

        top_species = conn.execute(
            "SELECT common_name, scientific_name, COUNT(*) as count "
            "FROM detections GROUP BY scientific_name "
            "ORDER BY count DESC LIMIT 10"
        ).fetchall()

        return {
            "total_detections": total,
            "unique_species": unique_species,
            "today_count": today_count,
            "week_count": week_count,
            "top_species": [dict(r) for r in top_species],
        }

    return _execute_with_retry(_get_db_path(data_dir), _query)


def get_detections(data_dir: str, date: str = None, species: str = None,
                   limit: int = 100) -> list[dict]:
    """Query detections with optional filters."""
    def _query(conn):
        query = "SELECT * FROM detections WHERE 1=1"
        params = []
        if date:
            query += " AND date = ?"
            params.append(date)
        if species:
            query += " AND (scientific_name = ? OR common_name = ?)"
            params.extend([species, species])
        query += " ORDER BY date DESC, time DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    return _execute_with_retry(_get_db_path(data_dir), _query)


def get_species(data_dir: str) -> list[dict]:
    """List all detected species with counts."""
    def _query(conn):
        rows = conn.execute(
            "SELECT common_name, scientific_name, COUNT(*) as count, "
            "MAX(confidence) as max_confidence, MAX(date) as last_seen "
            "FROM detections GROUP BY scientific_name "
            "ORDER BY count DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    return _execute_with_retry(_get_db_path(data_dir), _query)
