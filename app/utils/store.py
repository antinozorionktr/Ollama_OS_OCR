"""
Persistent Store — SQLite-backed storage for OCR results and batch state.
Survives browser refreshes, VPN disconnects, and container restarts.
The DB file is mounted to the host via Docker volume.
"""

import sqlite3
import json
import os
import threading
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

from app.core.config import get_settings

settings = get_settings()
DB_PATH = settings.db_path


class PersistentStore:
    """Thread-safe SQLite store for OCR results and batch job state."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._local = threading.local()
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a thread-local connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, timeout=30)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA busy_timeout=5000")
        return self._local.conn

    @contextmanager
    def _cursor(self):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_tables(self):
        with self._cursor() as cur:
            # ── OCR Results ──
            cur.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name   TEXT NOT NULL,
                    file_path   TEXT NOT NULL,
                    doc_type    TEXT NOT NULL,
                    raw_text    TEXT,
                    structured_data TEXT,
                    page_count  INTEGER DEFAULT 0,
                    processing_time_seconds REAL,
                    error       TEXT,
                    processed_at TEXT NOT NULL,
                    batch_id    TEXT,
                    created_at  TEXT DEFAULT (datetime('now'))
                )
            """)

            # ── Batch Jobs ──
            cur.execute("""
                CREATE TABLE IF NOT EXISTS batches (
                    id          TEXT PRIMARY KEY,
                    status      TEXT NOT NULL DEFAULT 'running',
                    total_files INTEGER NOT NULL,
                    completed   INTEGER NOT NULL DEFAULT 0,
                    failed      INTEGER NOT NULL DEFAULT 0,
                    started_at  TEXT NOT NULL,
                    finished_at TEXT,
                    config      TEXT
                )
            """)

            # ── Batch Queue (tracks individual files in a batch) ──
            cur.execute("""
                CREATE TABLE IF NOT EXISTS batch_queue (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id    TEXT NOT NULL,
                    file_path   TEXT NOT NULL,
                    doc_type    TEXT NOT NULL,
                    status      TEXT NOT NULL DEFAULT 'pending',
                    result_id   INTEGER,
                    error       TEXT,
                    duration_s  REAL,
                    FOREIGN KEY (batch_id) REFERENCES batches(id),
                    FOREIGN KEY (result_id) REFERENCES results(id)
                )
            """)

            # ── Index for fast lookups ──
            cur.execute("CREATE INDEX IF NOT EXISTS idx_results_batch ON results(batch_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_queue_batch ON batch_queue(batch_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON batch_queue(batch_id, status)")

    # ─────────────────────────────────────
    # RESULTS CRUD
    # ─────────────────────────────────────

    def save_result(self, result: dict, batch_id: Optional[str] = None) -> int:
        """Save a processing result. Returns the row ID."""
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO results (file_name, file_path, doc_type, raw_text,
                    structured_data, page_count, processing_time_seconds, error,
                    processed_at, batch_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.get("file_name", ""),
                result.get("file_path", ""),
                result.get("doc_type", ""),
                result.get("raw_text", ""),
                json.dumps(result.get("structured_data", {})),
                result.get("page_count", 0),
                result.get("processing_time_seconds"),
                result.get("error"),
                result.get("processed_at", datetime.now().isoformat()),
                batch_id,
            ))
            return cur.lastrowid

    def get_all_results(self, doc_type: Optional[str] = None) -> list[dict]:
        """Get all results, optionally filtered by doc_type."""
        with self._cursor() as cur:
            if doc_type:
                cur.execute(
                    "SELECT * FROM results WHERE doc_type = ? ORDER BY id DESC", (doc_type,)
                )
            else:
                cur.execute("SELECT * FROM results ORDER BY id DESC")
            rows = cur.fetchall()
        return [self._row_to_result(r) for r in rows]

    def get_result(self, result_id: int) -> Optional[dict]:
        """Get a single result by ID."""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM results WHERE id = ?", (result_id,))
            row = cur.fetchone()
        if not row:
            return None
        return self._row_to_result(row)

    def get_results_count(self) -> dict:
        """Get count of results grouped by doc_type."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT doc_type, COUNT(*) as cnt FROM results GROUP BY doc_type"
            )
            rows = cur.fetchall()
        return {row["doc_type"]: row["cnt"] for row in rows}

    def delete_all_results(self):
        """Delete all results."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM results")
            cur.execute("DELETE FROM batch_queue")
            cur.execute("DELETE FROM batches")

    def is_file_processed(self, file_path: str, batch_id: Optional[str] = None) -> bool:
        """Check if a file has already been successfully processed."""
        with self._cursor() as cur:
            if batch_id:
                cur.execute(
                    "SELECT 1 FROM results WHERE file_path = ? AND batch_id = ? AND error IS NULL LIMIT 1",
                    (file_path, batch_id),
                )
            else:
                cur.execute(
                    "SELECT 1 FROM results WHERE file_path = ? AND error IS NULL LIMIT 1",
                    (file_path,),
                )
            return cur.fetchone() is not None

    # ─────────────────────────────────────
    # BATCH MANAGEMENT
    # ─────────────────────────────────────

    def create_batch(self, batch_id: str, files: list[tuple[str, str]], config: dict = None) -> str:
        """
        Create a new batch job with its file queue.
        files: list of (file_path, doc_type) tuples.
        """
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO batches (id, status, total_files, started_at, config)
                VALUES (?, 'running', ?, ?, ?)
            """, (batch_id, len(files), datetime.now().isoformat(),
                  json.dumps(config) if config else None))

            for file_path, doc_type in files:
                cur.execute("""
                    INSERT INTO batch_queue (batch_id, file_path, doc_type, status)
                    VALUES (?, ?, ?, 'pending')
                """, (batch_id, file_path, doc_type))

        return batch_id

    def get_batch(self, batch_id: str) -> Optional[dict]:
        """Get batch metadata."""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM batches WHERE id = ?", (batch_id,))
            row = cur.fetchone()
        if not row:
            return None
        return dict(row)

    def get_pending_files(self, batch_id: str) -> list[dict]:
        """Get files that still need processing in a batch."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM batch_queue WHERE batch_id = ? AND status = 'pending' ORDER BY id",
                (batch_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    def get_batch_queue(self, batch_id: str) -> list[dict]:
        """Get all files in a batch queue with their status."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM batch_queue WHERE batch_id = ? ORDER BY id",
                (batch_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    def mark_file_done(self, batch_id: str, file_path: str, result_id: int, duration_s: float):
        """Mark a file as completed in the batch queue."""
        with self._cursor() as cur:
            cur.execute("""
                UPDATE batch_queue SET status = 'done', result_id = ?, duration_s = ?
                WHERE batch_id = ? AND file_path = ?
            """, (result_id, duration_s, batch_id, file_path))
            cur.execute("""
                UPDATE batches SET completed = completed + 1 WHERE id = ?
            """, (batch_id,))

    def mark_file_error(self, batch_id: str, file_path: str, error: str, duration_s: float):
        """Mark a file as failed in the batch queue."""
        with self._cursor() as cur:
            cur.execute("""
                UPDATE batch_queue SET status = 'error', error = ?, duration_s = ?
                WHERE batch_id = ? AND file_path = ?
            """, (error, duration_s, batch_id, file_path))
            cur.execute("""
                UPDATE batches SET failed = failed + 1 WHERE id = ?
            """, (batch_id,))

    def finish_batch(self, batch_id: str, status: str = "completed"):
        """Mark a batch as finished."""
        with self._cursor() as cur:
            cur.execute("""
                UPDATE batches SET status = ?, finished_at = ? WHERE id = ?
            """, (status, datetime.now().isoformat(), batch_id))

    def get_active_batch(self) -> Optional[dict]:
        """Get the most recent running or resumable batch."""
        with self._cursor() as cur:
            cur.execute("""
                SELECT * FROM batches WHERE status IN ('running', 'interrupted')
                ORDER BY started_at DESC LIMIT 1
            """)
            row = cur.fetchone()
        if not row:
            return None
        return dict(row)

    def interrupt_active_batches(self):
        """Mark all running batches as interrupted (called on startup to detect crashed batches)."""
        with self._cursor() as cur:
            cur.execute("""
                UPDATE batches SET status = 'interrupted'
                WHERE status = 'running'
            """)

    def get_batch_stats(self, batch_id: str) -> dict:
        """Get detailed stats for a batch."""
        batch = self.get_batch(batch_id)
        if not batch:
            return {}

        with self._cursor() as cur:
            cur.execute(
                "SELECT status, COUNT(*) as cnt FROM batch_queue WHERE batch_id = ? GROUP BY status",
                (batch_id,),
            )
            status_counts = {r["status"]: r["cnt"] for r in cur.fetchall()}

            cur.execute(
                "SELECT AVG(duration_s) as avg_dur FROM batch_queue WHERE batch_id = ? AND status = 'done'",
                (batch_id,),
            )
            avg_row = cur.fetchone()
            avg_duration = avg_row["avg_dur"] if avg_row and avg_row["avg_dur"] else 0

        pending = status_counts.get("pending", 0)
        done = status_counts.get("done", 0)
        errors = status_counts.get("error", 0)
        total = batch["total_files"]

        return {
            "batch_id": batch_id,
            "status": batch["status"],
            "total_files": total,
            "done": done,
            "errors": errors,
            "pending": pending,
            "progress_pct": round((done + errors) / total * 100, 1) if total > 0 else 0,
            "avg_duration_s": round(avg_duration, 1),
            "eta_seconds": round(pending * avg_duration, 1) if avg_duration else 0,
            "started_at": batch["started_at"],
            "finished_at": batch.get("finished_at"),
        }

    # ─────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────

    def _row_to_result(self, row) -> dict:
        """Convert a database row to a result dict."""
        d = dict(row)
        # Parse JSON fields
        if d.get("structured_data"):
            try:
                d["structured_data"] = json.loads(d["structured_data"])
            except (json.JSONDecodeError, TypeError):
                d["structured_data"] = {}
        else:
            d["structured_data"] = {}
        return d


# ─── Singleton ───
_store_instance: Optional[PersistentStore] = None


def get_store() -> PersistentStore:
    """Get or create the singleton store instance."""
    global _store_instance
    if _store_instance is None:
        _store_instance = PersistentStore()
    return _store_instance