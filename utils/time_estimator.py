"""
Time Estimator
Tracks per-document processing times and provides live ETA calculations
using a rolling average of recent processing durations.
"""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FileTimingRecord:
    """Record of a single file's processing timing."""
    file_name: str
    doc_type: str
    page_count: int
    start_time: float
    end_time: Optional[float] = None
    duration_s: Optional[float] = None
    status: str = "pending"  # pending | processing | done | error


class TimeEstimator:
    """
    Tracks processing durations and computes live ETAs.

    Strategy:
    - Maintains a rolling window of the last N completed file durations
    - Computes weighted average (recent files weighted more)
    - Provides per-page and per-file estimates
    - Falls back to a configurable default if no history yet
    """

    def __init__(self, window_size: int = 20, default_seconds_per_page: float = 30.0):
        self.window_size = window_size
        self.default_seconds_per_page = default_seconds_per_page
        self._history: deque[FileTimingRecord] = deque(maxlen=window_size)
        self._current: Optional[FileTimingRecord] = None
        self._batch_start: Optional[float] = None
        self._total_files: int = 0
        self._completed_files: int = 0

    def start_batch(self, total_files: int):
        """Begin a new batch processing run."""
        self._batch_start = time.time()
        self._total_files = total_files
        self._completed_files = 0

    def start_file(self, file_name: str, doc_type: str, page_count: int = 1) -> FileTimingRecord:
        """Mark a file as starting processing."""
        record = FileTimingRecord(
            file_name=file_name,
            doc_type=doc_type,
            page_count=max(page_count, 1),
            start_time=time.time(),
            status="processing",
        )
        self._current = record
        return record

    def finish_file(self, record: FileTimingRecord, status: str = "done"):
        """Mark a file as completed and record its timing."""
        record.end_time = time.time()
        record.duration_s = round(record.end_time - record.start_time, 2)
        record.status = status
        self._history.append(record)
        self._completed_files += 1
        self._current = None

    @property
    def avg_seconds_per_page(self) -> float:
        """Weighted average seconds per page from recent history."""
        if not self._history:
            return self.default_seconds_per_page

        total_weight = 0.0
        weighted_sum = 0.0
        for i, rec in enumerate(self._history):
            if rec.duration_s is None or rec.page_count == 0:
                continue
            weight = 1.0 + (i * 0.5)  # more recent = higher weight
            spp = rec.duration_s / rec.page_count
            weighted_sum += spp * weight
            total_weight += weight

        if total_weight == 0:
            return self.default_seconds_per_page
        return weighted_sum / total_weight

    @property
    def avg_seconds_per_file(self) -> float:
        """Simple average seconds per file from recent history."""
        completed = [r for r in self._history if r.duration_s is not None]
        if not completed:
            return self.default_seconds_per_page
        return sum(r.duration_s for r in completed) / len(completed)

    def estimate_remaining(self, remaining_files: int, avg_pages_per_file: float = 1.0) -> float:
        """Estimate seconds remaining for N files."""
        return remaining_files * avg_pages_per_file * self.avg_seconds_per_page

    def get_batch_stats(self) -> dict:
        """Return current batch processing statistics."""
        elapsed = time.time() - self._batch_start if self._batch_start else 0
        remaining_files = self._total_files - self._completed_files
        eta_seconds = self.estimate_remaining(remaining_files)

        return {
            "total_files": self._total_files,
            "completed_files": self._completed_files,
            "remaining_files": remaining_files,
            "elapsed_seconds": round(elapsed, 1),
            "eta_seconds": round(eta_seconds, 1),
            "avg_per_file_seconds": round(self.avg_seconds_per_file, 1),
            "avg_per_page_seconds": round(self.avg_seconds_per_page, 1),
            "progress_pct": round(
                (self._completed_files / self._total_files * 100) if self._total_files > 0 else 0,
                1,
            ),
        }

    def format_eta(self, seconds: float) -> str:
        """Format seconds into a human-readable string."""
        if seconds <= 0:
            return "Done"
        if seconds < 60:
            return f"{int(seconds)}s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        if minutes < 60:
            return f"{minutes}m {secs}s"
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        return f"{hours}h {mins}m"

    def get_current_file_elapsed(self) -> Optional[float]:
        """Get elapsed time for the currently processing file."""
        if self._current and self._current.status == "processing":
            return round(time.time() - self._current.start_time, 1)
        return None