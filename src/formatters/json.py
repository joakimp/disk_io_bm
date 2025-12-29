"""JSON output formatter for benchmark results"""

import json
from pathlib import Path
from typing import List
from datetime import datetime


class JsonFormatter:
    """JSON output formatter"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def format(self, results: List[dict]) -> None:
        """Format results as JSON and save to file"""
        timestamp = datetime.now().isoformat()

        output_file = self.output_dir / "benchmark_results.json"

        with open(output_file, "w") as f:
            json.dump({"timestamp": timestamp, "results": results}, f, indent=2)

        print(f"Results saved to {output_file}")
