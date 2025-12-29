"""SQLite storage backend for benchmark results"""

import sqlite3
from pathlib import Path
from typing import List
import json


class SQLiteStorage:
    """SQLite database storage for benchmark results"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS benchmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    mode TEXT,
                    filesize TEXT,
                    runtime INTEGER,
                    test_type TEXT,
                    block_size TEXT,
                    read_iops REAL,
                    write_iops REAL,
                    read_bw REAL,
                    write_bw REAL,
                    read_latency_us REAL,
                    write_latency_us REAL,
                    cpu TEXT,
                    status TEXT,
                    runtime_sec REAL,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON benchmarks(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_test_type ON benchmarks(test_type)
            """)
            conn.commit()

    def save_results(self, results: List[dict], config) -> None:
        """Save benchmark results to database"""
        with sqlite3.connect(self.db_path) as conn:
            for result in results:
                conn.execute(
                    """
                    INSERT INTO benchmarks (
                        mode, filesize, runtime, test_type, block_size,
                        read_iops, write_iops, read_bw, write_bw,
                        read_latency_us, write_latency_us, cpu, status, runtime_sec, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        config.mode.value if hasattr(config.mode, "value") else str(config.mode),
                        config.filesize,
                        config.runtime,
                        result.get("test_type", ""),
                        result.get("block_size", ""),
                        result.get("read_iops", 0),
                        result.get("write_iops", 0),
                        result.get("read_bw", 0),
                        result.get("write_bw", 0),
                        result.get("read_latency_us", 0),
                        result.get("write_latency_us", 0),
                        result.get("cpu", ""),
                        result.get("status", ""),
                        result.get("runtime_sec", 0),
                        json.dumps(result),
                    ),
                )
            conn.commit()

    def get_history(self, limit: int = 10) -> List[dict]:
        """Get recent benchmark results"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM benchmarks
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (limit,),
            )
            return [dict(row) for row in cursor]

    def custom_query(self, sql: str) -> List[dict]:
        """Execute custom SQL query"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql)
            return [dict(row) for row in cursor]
