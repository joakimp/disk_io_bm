"""Statistics and analysis for benchmark results"""

import pandas as pd
from typing import List, Dict, Any


class Statistics:
    """Calculate statistics for benchmark results"""

    @staticmethod
    def calculate_basic(results: List[dict]) -> Dict[str, Any]:
        """Calculate basic statistics (mean, median, min, max)"""
        if not results:
            return {}

        df = pd.DataFrame(results)

        numeric_cols = [
            "read_iops",
            "write_iops",
            "read_bw",
            "write_bw",
            "read_latency_us",
            "write_latency_us",
            "io_time_sec",
            "wall_time_sec",
        ]

        stats = {}

        for test_type in df["test_type"].unique():
            for block_size in df[df["test_type"] == test_type]["block_size"].unique():
                subset = df[(df["test_type"] == test_type) & (df["block_size"] == block_size)]

                if subset.empty:
                    continue

                key = f"{test_type}_{block_size}"
                stats[key] = {}

                for col in numeric_cols:
                    if col in subset.columns:
                        values = subset[col].dropna()
                        if len(values) > 0:
                            stats[key][col] = {
                                "mean": float(values.mean()),
                                "median": float(values.median()),
                                "min": float(values.min()),
                                "max": float(values.max()),
                            }

        return stats

    @staticmethod
    def calculate_detailed(results: List[dict]) -> Dict[str, Any]:
        """Calculate detailed statistics with std dev and percentiles"""
        basic_stats = Statistics.calculate_basic(results)

        if not results:
            return basic_stats

        df = pd.DataFrame(results)

        numeric_cols = [
            "read_iops",
            "write_iops",
            "read_bw",
            "write_bw",
            "read_latency_us",
            "write_latency_us",
            "io_time_sec",
            "wall_time_sec",
        ]

        for test_type in df["test_type"].unique():
            for block_size in df[df["test_type"] == test_type]["block_size"].unique():
                subset = df[(df["test_type"] == test_type) & (df["block_size"] == block_size)]

                if subset.empty:
                    continue

                key = f"{test_type}_{block_size}"

                for col in numeric_cols:
                    if col in subset.columns and col in basic_stats.get(key, {}):
                        values = subset[col].dropna()
                        if len(values) > 0:
                            basic_stats[key][col]["std"] = float(values.std())
                            basic_stats[key][col]["q25"] = float(values.quantile(0.25))
                            basic_stats[key][col]["q75"] = float(values.quantile(0.75))
                            basic_stats[key][col]["count"] = len(values)

        return basic_stats

    @staticmethod
    def format_basic(stats: Dict[str, Any]) -> str:
        """Format basic statistics for display"""
        if not stats:
            return "No statistics available"

        lines = ["Statistics Summary", "=" * 80]

        for key, metrics in stats.items():
            lines.append(f"\n{key}:")
            for metric, values in metrics.items():
                if "mean" in values:
                    lines.append(
                        f"  {metric}: mean={values['mean']:.2f}, "
                        f"median={values['median']:.2f}, "
                        f"min={values['min']:.2f}, "
                        f"max={values['max']:.2f}"
                    )

        return "\n".join(lines)

    @staticmethod
    def format_detailed(stats: Dict[str, Any]) -> str:
        """Format detailed statistics for display"""
        if not stats:
            return "No statistics available"

        lines = ["Detailed Statistics", "=" * 80]

        for key, metrics in stats.items():
            lines.append(f"\n{key}:")
            for metric, values in metrics.items():
                if "mean" in values:
                    lines.append(f"  {metric}:")
                    lines.append(f"    mean={values['mean']:.2f}, median={values['median']:.2f}")
                    lines.append(f"    std={values.get('std', 'N/A'):.2f}")
                    lines.append(f"    min={values['min']:.2f}, max={values['max']:.2f}")
                    if "q25" in values:
                        lines.append(f"    q25={values['q25']:.2f}, q75={values['q75']:.2f}")
                    if "count" in values:
                        lines.append(f"    count={values['count']}")

        return "\n".join(lines)
