"""Run comparison logic for benchmark results"""

import pandas as pd
from typing import List, Dict, Any, Tuple


class Comparison:
    """Compare benchmark runs"""

    @staticmethod
    def compare_runs(run1: List[dict], run2: List[dict], threshold: float = 0.1) -> Dict[str, Any]:
        """Compare two benchmark runs and calculate deltas"""
        if not run1 or not run2:
            return {"error": "Cannot compare empty runs"}

        df1 = pd.DataFrame(run1)
        df2 = pd.DataFrame(run2)

        comparison = {"run1": run1, "run2": run2, "deltas": [], "significant_changes": []}

        numeric_cols = [
            "read_iops",
            "write_iops",
            "read_bw",
            "write_bw",
            "read_latency_us",
            "write_latency_us",
        ]

        for _, row1 in df1.iterrows():
            test_type = row1["test_type"]
            block_size = row1["block_size"]

            matching = df2[(df2["test_type"] == test_type) & (df2["block_size"] == block_size)]

            if matching.empty:
                continue

            row2 = matching.iloc[0]

            delta = {"test_type": test_type, "block_size": block_size}

            for col in numeric_cols:
                val1 = row1.get(col, 0) or 0
                val2 = row2.get(col, 0) or 0

                delta_abs = val2 - val1
                delta_pct = (delta_abs / val1 * 100) if val1 != 0 else 0

                delta[f"{col}_abs"] = delta_abs
                delta[f"{col}_pct"] = delta_pct

                if abs(delta_pct) >= threshold * 100:
                    if "significant_fields" not in delta:
                        delta["significant_fields"] = []
                    delta["significant_fields"].append(col)

            comparison["deltas"].append(delta)

            if "significant_fields" in delta and delta["significant_fields"]:
                comparison["significant_changes"].append(delta)

        return comparison

    @staticmethod
    def format_comparison(comparison: Dict[str, Any]) -> str:
        """Format comparison for display as table"""
        if "error" in comparison:
            return comparison["error"]

        lines = ["Run Comparison", "=" * 100]

        for delta in comparison["deltas"]:
            lines.append(f"\n{delta['test_type']} ({delta['block_size']}):")

            if delta.get("significant_fields"):
                lines.append("  [SIGNIFICANT CHANGES]")
                for field in delta["significant_fields"]:
                    abs_change = delta[f"{field}_abs"]
                    pct_change = delta[f"{field}_pct"]
                    lines.append(f"    {field}: {abs_change:+.2f} ({pct_change:+.1f}%)")

                other_fields = [
                    f
                    for f in delta
                    if f not in ["test_type", "block_size", "significant_fields"]
                    and not f.endswith("_abs")
                    and not f.endswith("_pct")
                ]
                if other_fields:
                    lines.append("  [Other metrics]")
                    for field in other_fields:
                        if field.endswith("_abs") or field.endswith("_pct"):
                            continue
                        if field in delta:
                            abs_change = delta[f"{field}_abs"]
                            pct_change = delta[f"{field}_pct"]
                            lines.append(f"    {field}: {abs_change:+.2f} ({pct_change:+.1f}%)")
            else:
                for field in [
                    "read_iops",
                    "write_iops",
                    "read_bw",
                    "write_bw",
                    "read_latency_us",
                    "write_latency_us",
                ]:
                    if field in delta:
                        abs_change = delta[f"{field}_abs"]
                        pct_change = delta[f"{field}_pct"]
                        lines.append(f"  {field}: {abs_change:+.2f} ({pct_change:+.1f}%)")

        return "\n".join(lines)

    @staticmethod
    def get_last_n_runs(storage, n: int) -> Tuple[List[dict], List[dict]]:
        """Get last N runs from storage for comparison"""
        all_results = storage.get_history(n * 2)

        if len(all_results) < n:
            return [], []

        midpoint = len(all_results) // 2

        run1 = all_results[:midpoint]
        run2 = all_results[midpoint : midpoint * 2]

        return run1, run2
