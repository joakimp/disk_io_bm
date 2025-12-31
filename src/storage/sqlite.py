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
                    io_time_sec REAL,
                    wall_time_sec REAL,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON benchmarks(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_test_type ON benchmarks(test_type)
            """)
            # Migration: Add new columns if they don't exist (for existing databases)
            try:
                conn.execute("ALTER TABLE benchmarks ADD COLUMN io_time_sec REAL DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Column already exists
            try:
                conn.execute("ALTER TABLE benchmarks ADD COLUMN wall_time_sec REAL DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Column already exists
            # Migration: Copy runtime_sec to io_time_sec if runtime_sec exists
            try:
                conn.execute(
                    "UPDATE benchmarks SET io_time_sec = runtime_sec WHERE io_time_sec IS NULL OR io_time_sec = 0"
                )
            except sqlite3.OperationalError:
                pass  # runtime_sec column doesn't exist
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
                        read_latency_us, write_latency_us, cpu, status,
                        io_time_sec, wall_time_sec, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        result.get("io_time_sec", 0),
                        result.get("wall_time_sec", 0),
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

    def custom_query(self, sql: str, params: tuple = ()) -> List[dict]:
        """Execute custom SQL query"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if params:
                cursor = conn.execute(sql, params)
            else:
                cursor = conn.execute(sql)
            return [dict(row) for row in cursor]

    def get_statistics(self, detailed: bool = False) -> dict:
        """Calculate statistics from stored benchmarks"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM benchmarks")
            results = [dict(row) for row in cursor]

        if not results:
            return {}

        from src.analytics import Statistics

        if detailed:
            return Statistics.calculate_detailed(results)
        else:
            return Statistics.calculate_basic(results)

    def compare_runs(self, run_id1: int, run_id2: int, threshold: float = 0.1) -> dict:
        """Compare two specific runs"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor1 = conn.execute("SELECT * FROM benchmarks WHERE id=?", (run_id1,))
            cursor2 = conn.execute("SELECT * FROM benchmarks WHERE id=?", (run_id2,))
            run1 = [dict(row) for row in cursor1]
            run2 = [dict(row) for row in cursor2]

        if not run1 or not run2:
            return {"error": "One or both run IDs not found"}

        from src.analytics import Comparison

        return Comparison.compare_runs(run1, run2, threshold)

    def export_to_excel(self, filepath: str, filters: dict = None) -> None:
        """Export database to Excel with multiple sheets"""
        import pandas as pd

        query = "SELECT * FROM benchmarks WHERE 1=1"
        params = []

        if filters:
            if filters.get("after"):
                query += " AND timestamp >= ?"
                params.append(filters["after"])
            if filters.get("before"):
                query += " AND timestamp <= ?"
                params.append(filters["before"])
            if filters.get("test_type"):
                placeholders = ",".join(["?" for _ in filters["test_type"]])
                query += f" AND test_type IN ({placeholders})"
                params.extend(filters["test_type"])
            if filters.get("block_size"):
                placeholders = ",".join(["?" for _ in filters["block_size"]])
                query += f" AND block_size IN ({placeholders})"
                params.extend(filters["block_size"])

        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=params if params else ())

        if df.empty:
            print("No data to export")
            return

        with pd.ExcelWriter(
            filepath, engine="openpyxl", datetime_format="YYYY-MM-DD HH:MM:SS"
        ) as writer:
            summary_df = df.groupby(["test_type", "block_size"]).agg(
                {
                    "read_iops": ["mean", "min", "max"],
                    "write_iops": ["mean", "min", "max"],
                    "read_bw": ["mean", "min", "max"],
                    "write_bw": ["mean", "min", "max"],
                }
            )
            summary_df.columns = ["_".join(col).strip() for col in summary_df.columns.values]
            summary_df.reset_index(inplace=True)
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

            raw_df = df[
                [
                    "id",
                    "timestamp",
                    "test_type",
                    "block_size",
                    "read_iops",
                    "write_iops",
                    "read_bw",
                    "write_bw",
                    "read_latency_us",
                    "write_latency_us",
                    "cpu",
                    "io_time_sec",
                    "wall_time_sec",
                    "status",
                ]
            ]
            raw_df.to_excel(writer, sheet_name="Raw", index=False)

        print(f"Exported to {filepath}")
