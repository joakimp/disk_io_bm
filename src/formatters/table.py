"""Table output formatter for benchmark results"""

from typing import List, Optional
from rich.console import Console
from rich.table import Table


class TableFormatter:
    """Rich table output formatter"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def _format_time(self, seconds: float) -> str:
        """Format time value intelligently based on magnitude"""
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        else:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes:02d}:{secs:02d}"

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
        table.add_column("I/O Time", justify="right", style="white")
        table.add_column("Wall Time", justify="right", style="white")
        table.add_column("Status", justify="left", style="white")

        for result in results:
            # Support both old (runtime_sec) and new (io_time_sec) field names
            io_time = result.get("io_time_sec") or result.get("runtime_sec") or 0
            wall_time = result.get("wall_time_sec") or 0

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
                self._format_time(io_time),
                self._format_time(wall_time) if wall_time > 0 else "N/A",
                result.get("status", "N/A"),
            )

        self.console.print(table)
