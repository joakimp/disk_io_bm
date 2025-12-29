"""CSV file storage for benchmark results"""

import csv
from pathlib import Path
from typing import List
from datetime import datetime


class CsvStorage:
    """CSV file storage for benchmark results"""

    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def save_results(self, results: List[dict], config) -> None:
        """Save results as CSV with metadata comments"""
        timestamp = datetime.now().isoformat()

        output_file = self.results_dir / f"benchmark_{timestamp.replace(':', '-')}.csv"

        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)

            writer.writerow(["# Disk I/O Benchmark Results"])
            writer.writerow([f"# Timestamp: {timestamp}"])
            writer.writerow([f"# Mode: {config.mode.value}"])
            writer.writerow([f"# File Size: {config.filesize}"])
            writer.writerow([f"# Runtime: {config.runtime}s"])
            writer.writerow([f"# SSD: {config.ssd}"])
            writer.writerow([f"# Concurrency: {config.concurrency}"])
            writer.writerow([""])

            writer.writerow(
                [
                    "Test Type",
                    "Block Size",
                    "Read IOPS",
                    "Write IOPS",
                    "Read MB/s",
                    "Write MB/s",
                    "Read Lat (us)",
                    "Write Lat (us)",
                    "CPU",
                    "Runtime (s)",
                    "Status",
                ]
            )

            for result in results:
                writer.writerow(
                    [
                        result.get("test_type", "N/A"),
                        result.get("block_size", "N/A"),
                        (result.get("read_iops") or 0),
                        (result.get("write_iops") or 0),
                        f"{(result.get('read_bw') or 0) / 1024 / 1024:.2f}",
                        f"{(result.get('write_bw') or 0) / 1024 / 1024:.2f}",
                        f"{(result.get('read_latency_us') or 0):.2f}",
                        f"{(result.get('write_latency_us') or 0):.2f}",
                        result.get("cpu", "N/A"),
                        f"{(result.get('runtime_sec') or 0):.2f}",
                        result.get("status", "N/A"),
                    ]
                )
