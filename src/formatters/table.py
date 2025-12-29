"""Table output formatter for benchmark results"""

from typing import List, Optional
from rich.console import Console
from rich.table import Table


class TableFormatter:
    """Rich table output formatter"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def format(self, results: List[dict]) -> None:
        """Format results as a table"""
        if not results:
            self.console.print("[yellow]No results to display[/yellow]")
            return

        table = Table(title="Disk I/O Benchmark Results")

        table.add_column("Test Type", style="cyan", no_wrap=True)
        table.add_column("Block Size", style="magenta")
        table.add_column("Read IOPS", justify="right", style="green")
        table.add_column("Write IOPS", justify="right", style="green")
        table.add_column("Read MB/s", justify="right", style="blue")
        table.add_column("Write MB/s", justify="right", style="blue")
        table.add_column("Read Lat (µs)", justify="right", style="yellow")
        table.add_column("Write Lat (µs)", justify="right", style="yellow")
        table.add_column("CPU", justify="left", style="white")
        table.add_column("Runtime (s)", justify="right", style="white")
        table.add_column("Status", justify="left", style="white")

        for result in results:
            table.add_row(
                result.get("test_type", "N/A"),
                result.get("block_size", "N/A"),
                f"{(result.get('read_iops') or 0):.0f}",
                f"{(result.get('write_iops') or 0):.0f}",
                f"{(result.get('read_bw') or 0) / 1024 / 1024:.2f}",
                f"{(result.get('write_bw') or 0) / 1024 / 1024:.2f}",
                f"{(result.get('read_latency_us') or 0):.2f}",
                f"{(result.get('write_latency_us') or 0):.2f}",
                result.get("cpu", "N/A"),
                f"{(result.get('runtime_sec') or 0):.2f}",
                result.get("status", "N/A"),
            )

        self.console.print(table)
