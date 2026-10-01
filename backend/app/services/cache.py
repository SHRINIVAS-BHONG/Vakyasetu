from collections import OrderedDict
import hashlib
import json
import logging
import sqlite3
import threading
from typing import Optional, Dict, Any

from app.core.config import settings
from app.core.normalizer import SanskritNormalizer

logger = logging.getLogger(__name__)

class SQLiteCache:
    """
    Production-Grade Hybrid Two-Tier Caching Engine for VākyaSetu.
    
    Tier 1 (L1 In-Memory LRU Cache):
    - Sub-microsecond response time (< 0.05ms) for the hottest recurring queries.
    - Bounded memory footprint (defaults to 2,048 sentences) with LRU eviction.
    
    Tier 2 (L2 Persistent SQLite Cache):
    - Persistent across restarts, stored in SQLite WAL mode.
    - Uses SHA-256 sentence hashing and memory-mapped I/O (PRAGMA mmap_size=256MB).
    - Persistent connection re-use protected by mutex locks to eliminate connection overhead.
    - Compact JSON serialization (no unnecessary whitespace).
    """

    def __init__(self, db_path: Optional[str] = None, max_memory_entries: int = 2048):
        self.db_path = db_path or settings.CACHE_DB_PATH
        self.max_memory_entries = max_memory_entries
        self._lock = threading.Lock()
        
        # L1 In-Memory Cache (OrderedDict for O(1) LRU eviction)
        self._l1_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
        # Diagnostic Counters
        self._l1_hits = 0
        self._l2_hits = 0
        self._misses = 0

        # Initialize L2 SQLite Database
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Retrieves or creates the thread-safe persistent connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                self.db_path,
                timeout=15.0,
                check_same_thread=False
            )
            # High-performance PRAGMAs
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.execute("PRAGMA mmap_size=268435456;")  # 256MB memory-mapped I/O
            self._conn.execute("PRAGMA cache_size=-8000;")     # 8MB page cache
            self._conn.execute("PRAGMA temp_store=MEMORY;")    # In-memory temporary tables
            self._conn.execute("PRAGMA busy_timeout=5000;")    # 5s retry on concurrency
        return self._conn

    def _init_db(self) -> None:
        """Sets up the sentence_cache table with primary key hash_key."""
        with self._lock:
            conn = self._get_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sentence_cache (
                    hash_key TEXT PRIMARY KEY,
                    raw_text TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    hit_count INTEGER DEFAULT 1
                );
            """)
            conn.commit()

    @classmethod
    def compute_hash(cls, text: str) -> str:
        """
        Generates deterministic SHA-256 hash for normalized Sanskrit text.
        Ensures identical hash for texts varying only by zero-width characters or spacing.
        """
        if not text:
            return ""
        norm = SanskritNormalizer.normalize(text)
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached response:
        1. Checks Tier 1 (RAM LRU): Returns immediately in < 0.05ms.
        2. Checks Tier 2 (SQLite WAL): Updates hit count, promotes to Tier 1, and returns.
        3. Returns None on cache miss.
        """
        if not text:
            return None

        key = self.compute_hash(text)
        if not key:
            return None

        with self._lock:
            # 1. Check L1 Memory Cache
            if key in self._l1_cache:
                self._l1_cache.move_to_end(key)
                self._l1_hits += 1
                # Increment DB hit_count asynchronously/lightweight
                try:
                    conn = self._get_connection()
                    conn.execute("UPDATE sentence_cache SET hit_count = hit_count + 1 WHERE hash_key = ?", (key,))
                    conn.commit()
                except Exception:
                    pass
                return self._l1_cache[key]

            # 2. Check L2 SQLite Cache
            try:
                conn = self._get_connection()
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

                    # Populate L1 cache with LRU eviction
                    if len(self._l1_cache) >= self.max_memory_entries:
                        self._l1_cache.popitem(last=False)
                    self._l1_cache[key] = data
                    self._l2_hits += 1
                    return data
            except Exception as e:
                logger.error(f"Error reading from SQLite cache for '{text}': {e}", exc_info=True)

            self._misses += 1
            return None

    def set(self, text: str, data: Dict[str, Any]) -> None:
        """
        Writes to both Tier 1 (RAM) and Tier 2 (SQLite WAL).
        Uses compact JSON serialization to optimize storage and cache performance.
        """
        if not text:
            return
        key = self.compute_hash(text)
        if not key:
            return

        # Compact serialization without redundant whitespaces
        payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

        with self._lock:
            # 1. Update L1 RAM Cache
            if len(self._l1_cache) >= self.max_memory_entries:
                self._l1_cache.popitem(last=False)
            self._l1_cache[key] = data

            # 2. Upsert into L2 SQLite Cache
            try:
                conn = self._get_connection()
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
        """Returns deep telemetry metrics on caching performance."""
        with self._lock:
            total_requests = self._l1_hits + self._l2_hits + self._misses
            hit_ratio = (
                round(((self._l1_hits + self._l2_hits) / total_requests) * 100, 2)
                if total_requests > 0 else 0.0
            )

            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*), COALESCE(SUM(hit_count), 0) FROM sentence_cache;")
                total_records, total_db_hits = cursor.fetchone()
                return {
                    "total_cached_sentences": total_records,
                    "total_hits": total_db_hits,
                    "total_db_hits": total_db_hits,
                    "l1_memory_hits": self._l1_hits,
                    "l2_sqlite_hits": self._l2_hits,
                    "cache_misses": self._misses,
                    "hit_ratio_percent": hit_ratio,
                    "l1_cache_size": len(self._l1_cache),
                    "max_l1_capacity": self.max_memory_entries,
                    "db_path": self.db_path,
                }
            except Exception as e:
                logger.error(f"Error querying cache stats: {e}", exc_info=True)
                return {"error": str(e)}

    def clear(self) -> None:
        """Purges both L1 in-memory and L2 SQLite cache stores."""
        with self._lock:
            self._l1_cache.clear()
            self._l1_hits = 0
            self._l2_hits = 0
            self._misses = 0
            if self._conn:
                self._conn.execute("DELETE FROM sentence_cache;")
                self._conn.commit()

    def close(self) -> None:
        """Safely closes the SQLite connection."""
        with self._lock:
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

_global_cache_instance: Optional[SQLiteCache] = None
_global_cache_lock = threading.Lock()

def get_cache(db_path: Optional[str] = None) -> SQLiteCache:
    """Provides application-wide singleton SQLiteCache instance."""
    global _global_cache_instance
    if _global_cache_instance is None:
        with _global_cache_lock:
            if _global_cache_instance is None:
                _global_cache_instance = SQLiteCache(db_path=db_path)
    return _global_cache_instance

