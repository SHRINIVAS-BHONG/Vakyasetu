import sqlite3
import hashlib
import json
import logging
import threading
from typing import Optional, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

class SQLiteCache:
    """
    High-Performance, Thread-Safe SQLite Caching Engine for VākyaSetu.
    Caches complete pipeline JSON responses keyed by SHA-256 hash of normalized Sanskrit sentences.
    Provides sub-millisecond retrieval on cache hits and tracks cumulative query hit counts.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.CACHE_DB_PATH
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Creates a connection configured for high-concurrency WAL mode."""
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        """Initializes the cache schema and index if not already present."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sentence_cache (
                        hash_key TEXT PRIMARY KEY,
                        raw_text TEXT NOT NULL,
                        response_json TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        hit_count INTEGER DEFAULT 1
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_hash ON sentence_cache(hash_key);")
                conn.commit()

    @staticmethod
    def compute_hash(text: str) -> str:
        """Generates deterministic SHA-256 hash for normalized Sanskrit text."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached response JSON for a given text.
        If found, increments the hit count and returns the deserialized dictionary.
        Returns None on cache miss.
        """
        key = self.compute_hash(text)
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT response_json, hit_count FROM sentence_cache WHERE hash_key = ?",
                        (key,)
                    )
                    row = cursor.fetchone()
                    if row:
                        response_json, hit_count = row
                        cursor.execute(
                            "UPDATE sentence_cache SET hit_count = hit_count + 1 WHERE hash_key = ?",
                            (key,)
                        )
                        conn.commit()
                        data = json.loads(response_json)
                        return data
            except Exception as e:
                logger.error(f"Error reading from SQLite cache for '{text}': {e}", exc_info=True)
        return None

    def set(self, text: str, data: Dict[str, Any]) -> None:
        """
        Inserts or updates a cached pipeline response for the given text.
        Serializes data to UTF-8 JSON.
        """
        key = self.compute_hash(text)
        payload = json.dumps(data, ensure_ascii=False)
        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT INTO sentence_cache (hash_key, raw_text, response_json)
                        VALUES (?, ?, ?)
                        ON CONFLICT(hash_key) DO UPDATE SET
                            response_json = excluded.response_json,
                            hit_count = hit_count + 1;
                    """, (key, text.strip(), payload))
                    conn.commit()
            except Exception as e:
                logger.error(f"Error writing to SQLite cache for '{text}': {e}", exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        """Returns diagnostic statistics about cache utilization."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*), COALESCE(SUM(hit_count), 0) FROM sentence_cache;")
                    total_records, total_hits = cursor.fetchone()
                    return {
                        "total_cached_sentences": total_records,
                        "total_hits": total_hits,
                        "db_path": self.db_path,
                    }
            except Exception as e:
                logger.error(f"Error querying cache stats: {e}", exc_info=True)
                return {"error": str(e)}

    def clear(self) -> None:
        """Clears all records from the cache."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM sentence_cache;")
                conn.commit()
