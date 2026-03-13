"""
Persistent Store — SQLite-backed storage for documents and page-wise OCR results.
New schema: documents + document_pages (no bounding boxes, no tokens).
"""

import sqlite3
import os
import threading
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

from app.core.config import get_settings

settings = get_settings()
DB_PATH = settings.db_path


class PersistentStore:
    """Thread-safe SQLite store for documents and page-level OCR results."""

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
            # ── Documents ──
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename        TEXT NOT NULL,
                    file_path       TEXT NOT NULL,
                    uploaded_at     TEXT NOT NULL,
                    total_pages     INTEGER DEFAULT 0,
                    processing_time_seconds REAL,
                    error           TEXT
                )
            """)

            # ── Document Pages ──
            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_pages (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id     INTEGER NOT NULL,
                    page_number     INTEGER NOT NULL,
                    raw_text        TEXT,
                    cleaned_text    TEXT,
                    recreated_layout TEXT,
                    structured_data TEXT,  -- New column for key-value pairs
                    created_at      TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)

            # ── Indexes ──
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pages_doc ON document_pages(document_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pages_doc_page ON document_pages(document_id, page_number)")

    # ─────────────────────────────────────
    # DOCUMENTS CRUD
    # ─────────────────────────────────────

    def save_document(
        self,
        filename: str,
        file_path: str,
        total_pages: int = 0,
        processing_time_seconds: float = None,
        error: str = None,
    ) -> int:
        """Save a new document record. Returns the document ID."""
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO documents (filename, file_path, uploaded_at, total_pages,
                    processing_time_seconds, error)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                filename,
                file_path,
                datetime.now().isoformat(),
                total_pages,
                processing_time_seconds,
                error,
            ))
            return cur.lastrowid

    def update_document(
        self,
        document_id: int,
        total_pages: int = None,
        processing_time_seconds: float = None,
        error: str = None,
    ):
        """Update a document record after processing."""
        with self._cursor() as cur:
            updates = []
            values = []
            if total_pages is not None:
                updates.append("total_pages = ?")
                values.append(total_pages)
            if processing_time_seconds is not None:
                updates.append("processing_time_seconds = ?")
                values.append(processing_time_seconds)
            if error is not None:
                updates.append("error = ?")
                values.append(error)
            if updates:
                values.append(document_id)
                cur.execute(
                    f"UPDATE documents SET {', '.join(updates)} WHERE id = ?",
                    tuple(values),
                )

    def get_document(self, document_id: int) -> Optional[dict]:
        """Get a single document by ID."""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
            row = cur.fetchone()
        if not row:
            return None
        return dict(row)

    def get_all_documents(self) -> list[dict]:
        """Get all documents, ordered by most recent first."""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM documents ORDER BY id DESC")
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def get_documents_count(self) -> int:
        """Get total document count."""
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM documents")
            row = cur.fetchone()
        return row["cnt"] if row else 0

    def delete_document(self, document_id: int) -> bool:
        """Delete a document and all its pages."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM document_pages WHERE document_id = ?", (document_id,))
            cur.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            return cur.rowcount > 0

    def delete_all_documents(self):
        """Delete all documents and pages."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM document_pages")
            cur.execute("DELETE FROM documents")

    # ─────────────────────────────────────
    # DOCUMENT PAGES CRUD
    # ─────────────────────────────────────

    def save_page_result(
        self,
        document_id: int,
        page_number: int,
        raw_text: str = None,
        cleaned_text: str = None,
        recreated_layout: str = None,
        structured_data: str = None,
    ) -> int:
        """Save a page-level result. Returns the page record ID."""
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO document_pages (document_id, page_number, raw_text,
                    cleaned_text, recreated_layout, structured_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                document_id,
                page_number,
                raw_text,
                cleaned_text,
                recreated_layout,
                structured_data,
            ))
            return cur.lastrowid

    def get_document_pages(self, document_id: int) -> list[dict]:
        """Get all pages for a document, ordered by page number."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM document_pages WHERE document_id = ? ORDER BY page_number",
                (document_id,),
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def get_page(self, document_id: int, page_number: int) -> Optional[dict]:
        """Get a single page by document ID and page number."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM document_pages WHERE document_id = ? AND page_number = ?",
                (document_id, page_number),
            )
            row = cur.fetchone()
        if not row:
            return None
        return dict(row)

    def update_page_structured_data(self, document_id: int, page_number: int, structured_data: str):
        """Update the structured_data column for a specific page."""
        with self._cursor() as cur:
            cur.execute("""
                UPDATE document_pages 
                SET structured_data = ? 
                WHERE document_id = ? AND page_number = ?
            """, (structured_data, document_id, page_number))


# ─── Singleton ───
_store_instance: Optional[PersistentStore] = None


def get_store() -> PersistentStore:
    """Get or create the singleton store instance."""
    global _store_instance
    if _store_instance is None:
        _store_instance = PersistentStore()
    return _store_instance