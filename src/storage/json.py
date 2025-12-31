"""JSON file storage for benchmark results"""

import json
from pathlib import Path
from typing import List
from datetime import datetime


class JsonStorage:
    """JSON file storage for benchmark results"""

    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def save_results(self, results: List[dict], config) -> None:
        """Save results as JSON"""
        timestamp = datetime.now().isoformat()

        # Handle both enum and string mode values
        mode_value = config.mode.value if hasattr(config.mode, "value") else str(config.mode)
        if mode_value == "individual":
            # Separate JSON files for individual tests
            for result in results:
                test_name = f"{result['test_type']}_{result['block_size']}"
                json_dir = self.results_dir / "json"
                json_dir.mkdir(parents=True, exist_ok=True)
                output_file = json_dir / f"{test_name}.json"

                # Support both old (runtime_sec) and new (io_time_sec) field names
                io_time = result.get("io_time_sec") or result.get("runtime_sec")
                wall_time = result.get("wall_time_sec")

                test_result = {
                    "timestamp": timestamp,
                    "test": result["test_type"],
                    "block_size": result["block_size"],
                    "read_iops": result.get("read_iops") if result.get("read_iops") else "N/A",
                    "write_iops": result.get("write_iops") if result.get("write_iops") else "N/A",
                    "read_bw_mibs": result.get("read_bw") if result.get("read_bw") else "N/A",
                    "write_bw_mibs": result.get("write_bw") if result.get("write_bw") else "N/A",
                    "read_latency_us": result.get("read_latency_us")
                    if result.get("read_latency_us")
                    else "N/A",
                    "write_latency_us": result.get("write_latency_us")
                    if result.get("write_latency_us")
                    else "N/A",
                    "cpu": result.get("cpu") if result.get("cpu") else "N/A",
                    "io_time_sec": io_time if io_time else "N/A",
                    "wall_time_sec": wall_time if wall_time else "N/A",
                }

                with open(output_file, "w") as f:
                    json.dump(test_result, f, indent=2)
        else:
            # Combined JSON file for lean/full modes
            output_file = self.results_dir / "benchmark_results.json"

            with open(output_file, "w") as f:
                json.dump(
                    {"timestamp": timestamp, "mode": mode_value, "results": results},
                    f,
                    indent=2,
                )
