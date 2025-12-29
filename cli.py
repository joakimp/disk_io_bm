"""Click-based CLI for disk I/O benchmarking"""

import click

from rich.console import Console
from rich.panel import Panel

from src.config import BenchmarkConfig, Mode, StorageBackend
from src.executor import BenchmarkExecutor
from src.storage import SQLiteStorage, JsonStorage
from src.formatters import TableFormatter, JsonFormatter


@click.group()
def main():
    """Disk I/O benchmarking tool"""
    pass


@main.command()
@click.option(
    "--mode",
    type=click.Choice(["test", "lean", "full", "individual"]),
    default="lean",
    help="Test mode",
)
@click.option("--ssd", is_flag=True, help="Enable SSD-specific tests")
@click.option("--hdd", is_flag=True, help="Enable HDD-specific tests")
@click.option("--concurrency", is_flag=True, help="High concurrency mode")
@click.option("--quick", is_flag=True, help="Quick mode (1G file, 15s runtime)")
@click.option(
    "--test-type",
    "test_type",
    multiple=True,
    type=click.Choice(["randread", "randwrite", "read", "write", "randrw", "trim"]),
    help="Individual test types",
)
@click.option(
    "--block-size",
    "block_size",
    multiple=True,
    type=click.Choice(["4k", "64k", "1M", "512k"]),
    help="Block sizes for individual tests",
)
@click.option("--runtime", type=int, default=300, help="Test runtime in seconds")
@click.option("--filesize", type=str, default="10G", help="File size for fio")
@click.option(
    "--output-format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format (table/json)",
)
@click.option(
    "--database",
    type=click.Choice(["none", "sqlite", "json"]),
    default="sqlite",
    help="Storage backend (none/sqlite/json)",
)
@click.option(
    "--db-path",
    "db_path",
    type=click.Path(),
    default="results/benchmark_history.db",
    help="Path to SQLite database file",
)
@click.option(
    "--history", type=int, default=0, help="Show N recent benchmark runs (history-only mode)"
)
@click.option("--query-sql", type=str, help="Query database with custom SQL (history-only mode)")
def run(**kwargs):
    """Run disk I/O benchmarks with fio"""
    console = Console()

    # Build configuration from CLI arguments
    config_data = {
        "mode": Mode(kwargs["mode"]),
        "ssd": kwargs["ssd"],
        "hdd": kwargs["hdd"],
        "concurrency": kwargs["concurrency"],
        "quick": kwargs["quick"],
        "test_types": list(kwargs["test_type"]),
        "block_sizes": list(kwargs["block_size"]),
        "runtime": kwargs["runtime"],
        "filesize": kwargs["filesize"],
        "results_dir": "results",
        "output_format": kwargs["output_format"],
        "json_output_dir": "results/json",
        "database": StorageBackend(kwargs["database"]),
        "db_path": kwargs["db_path"],
        "history": kwargs["history"],
        "query_sql": kwargs["query_sql"],
    }

    # Quick mode overrides
    if kwargs["quick"]:
        config_data["runtime"] = 15
        config_data["filesize"] = "1G"

    # Auto-detect individual mode
    if config_data["test_types"]:
        config_data["mode"] = Mode.INDIVIDUAL
        if not config_data["block_sizes"]:
            config_data["block_sizes"] = ["4k", "64k", "1M", "512k"]

    config = BenchmarkConfig.from_dict(config_data)

    # Handle history or query mode (only when explicitly requested)
    if config.history > 0 or config.query_sql:
        if config.database == StorageBackend.SQLITE:
            storage = SQLiteStorage(config.db_path)
            if config.query_sql:
                results = storage.custom_query(config.query_sql)
                console.print(Panel("Custom Query Results", style="blue"))
            else:
                results = storage.get_history(config.history)
                console.print(Panel(f"Last {config.history} Benchmark Runs", style="blue"))

            if results:
                formatter = TableFormatter(console)
                formatter.format(results)
            return
        else:
            console.print("[yellow]History and query only available with SQLite backend[/yellow]")
            return

    # Validate mode conflicts
    if config.mode == Mode.INDIVIDUAL and not config.test_types:
        console.print("[red]Error: Individual mode requires --test-type flags[/red]")
        return

    # Run benchmarks
    executor = BenchmarkExecutor(config, console)
    results = executor.run_all_tests()

    # Store results
    if config.database != StorageBackend.NONE:
        storage = None
        if config.database == StorageBackend.SQLITE:
            storage = SQLiteStorage(config.db_path)
        elif config.database == StorageBackend.JSON:
            storage = JsonStorage(config.results_dir)
        if storage:
            storage.save_results(results, config)

    # Format and display output
    if config.output_format == "table":
        formatter = TableFormatter(console)
        formatter.format(results)
    elif config.output_format == "json":
        formatter = JsonFormatter(config.json_output_dir)
        formatter.format(results)


@main.command()
@click.option(
    "--mode",
    type=click.Choice(["test", "lean", "full", "individual"]),
    default="test",
    help="Test mode",
)
@click.option("--ssd", is_flag=True, help="Enable SSD-specific tests")
@click.option("--concurrency", is_flag=True, help="High concurrency mode")
@click.option("--quick", is_flag=True, help="Quick mode")
@click.option(
    "--test-type",
    "test_type",
    multiple=True,
    type=click.Choice(["randread", "randwrite", "read", "write", "randrw", "trim"]),
    help="Individual test types",
)
@click.option(
    "--block-size",
    "block_size",
    multiple=True,
    type=click.Choice(["4k", "64k", "1M", "512k"]),
    help="Block sizes for individual tests",
)
@click.option("--runtime", type=int, default=15, help="Test runtime in seconds")
@click.option("--filesize", type=str, default="1G", help="File size for fio")
def test(**kwargs):
    """Run a quick test benchmark"""
    console = Console()

    config_data = {
        "mode": Mode(kwargs["mode"]),
        "ssd": kwargs["ssd"],
        "concurrency": kwargs["concurrency"],
        "quick": kwargs["quick"],
        "test_types": list(kwargs["test_type"]),
        "block_sizes": list(kwargs["block_size"]),
        "runtime": kwargs["runtime"],
        "filesize": kwargs["filesize"],
        "results_dir": "results",
        "output_format": "table",
        "database": StorageBackend.NONE,
    }

    config = BenchmarkConfig.from_dict(config_data)

    console.print("[blue]Running test benchmark...[/blue]")
    executor = BenchmarkExecutor(config, console)
    results = executor.run_all_tests()

    formatter = TableFormatter(console)
    formatter.format(results)
