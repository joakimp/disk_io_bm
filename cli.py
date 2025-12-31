"""Click-based CLI for disk I/O benchmarking"""

import click

from rich.console import Console
from rich.panel import Panel

from src.config import BenchmarkConfig, Mode, StorageBackend
from src.executor import BenchmarkExecutor
from src.storage import SQLiteStorage, JsonStorage, CsvStorage
from src.formatters import TableFormatter, JsonFormatter, CsvFormatter, ExcelFormatter
from src.plots import create_plotter
from src.analytics import Statistics, Comparison


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
    type=click.Choice(["table", "json", "csv", "excel"]),
    default="table",
    help="Output format (table/json/csv/excel)",
)
@click.option(
    "--database",
    type=click.Choice(["none", "sqlite", "json", "csv"]),
    default="sqlite",
    help="Storage backend (none/sqlite/json/csv)",
)
@click.option("--plots", is_flag=True, help="Generate plots after benchmark")
@click.option(
    "--plot-types",
    "plot_types",
    multiple=True,
    type=click.Choice(["bar", "scatter", "radar", "line"]),
    default=["bar", "scatter", "radar"],
    help="Plot types to generate",
)
@click.option(
    "--plot-output-dir", type=click.Path(), default="results/plots", help="Directory for plot files"
)
@click.option("--open-browser", is_flag=True, help="Open plots in browser after generation")
@click.option("--no-database", is_flag=True, help="Disable database storage (for dummy tests)")
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
        "database": StorageBackend.NONE
        if kwargs["no_database"]
        else StorageBackend(kwargs["database"]),
        "db_path": kwargs["db_path"],
        "history": kwargs["history"],
        "query_sql": kwargs["query_sql"],
        "generate_plots": kwargs["plots"],
        "plot_types": list(kwargs["plot_types"]),
        "plot_output_dir": kwargs["plot_output_dir"],
        "interactive_plots": kwargs["open_browser"],
    }

    # Quick mode overrides
    if kwargs["quick"]:
        config_data["runtime"] = 15
        config_data["filesize"] = "1G"

    # Test mode overrides (use shorter runtime and smaller filesize)
    if kwargs["mode"] == "test":
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
    import time

    start_time = time.time()
    executor = BenchmarkExecutor(config, console)
    results = executor.run_all_tests()
    total_wall_time = time.time() - start_time

    # Store results
    if config.database != StorageBackend.NONE:
        storage = None
        if config.database == StorageBackend.SQLITE:
            storage = SQLiteStorage(config.db_path)
        elif config.database == StorageBackend.JSON:
            storage = JsonStorage(config.results_dir)
        elif config.database == StorageBackend.CSV:
            storage = CsvStorage(config.results_dir)
        if storage:
            storage.save_results(results, config)

    # Format and display output
    if config.output_format == "table":
        formatter = TableFormatter(console)
        formatter.format(results)
    elif config.output_format == "json":
        formatter = JsonFormatter(config.json_output_dir)
        formatter.format(results)
    elif config.output_format == "csv":
        formatter = CsvFormatter("results/benchmark_results.csv")
        formatter.format(results)
    elif config.output_format == "excel":
        formatter = ExcelFormatter("results/benchmark_results.xlsx")
        formatter.format(results)

    # Display total runtime
    minutes, seconds = divmod(int(total_wall_time), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        time_str = f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        time_str = f"{minutes}m {seconds}s"
    else:
        time_str = f"{seconds}s"
    console.print(f"\nTotal runtime: [bold cyan]{time_str}[/bold cyan]")

    # Generate plots if requested
    if config.generate_plots and results:
        try:
            from glob import glob

            plotter = create_plotter(config.plot_types, results, config_data)
            plotter.generate()

            if config.interactive_plots:
                from glob import glob

                for plot_file in glob(str(config.plot_output_dir) + "/*.html"):
                    console.print(f"[green]Opening {plot_file} in browser...[/green]")
                    success = plotter.open_in_browser(plot_file)
                    if not success:
                        console.print(f"[yellow]Browser open failed for {plot_file}[/yellow]")
                        console.print(f"[dim]File saved at: {plot_file}[/dim]")

            console.print(f"[green]Plots saved to {config.plot_output_dir}/[/green]")
        except ImportError as e:
            console.print(f"[yellow]Could not import plotting libraries: {e}[/yellow]")
        except Exception as e:
            console.print(f"[red]Error generating plots: {e}[/red]")


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
    import time

    start_time = time.time()
    executor = BenchmarkExecutor(config, console)
    results = executor.run_all_tests()
    total_wall_time = time.time() - start_time

    formatter = TableFormatter(console)
    formatter.format(results)

    # Display total runtime
    minutes, seconds = divmod(int(total_wall_time), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        time_str = f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        time_str = f"{minutes}m {seconds}s"
    else:
        time_str = f"{seconds}s"
    console.print(f"\nTotal runtime: [bold cyan]{time_str}[/bold cyan]")


@main.command()
@click.option("--last", type=int, default=2, help="Compare last N runs")
@click.option("--run-ids", "run_ids", nargs=2, type=int, help="Compare specific run IDs")
@click.option("--plots", is_flag=True, help="Generate comparison plots")
@click.option("--statistics", is_flag=True, help="Show statistical analysis")
@click.option(
    "--threshold",
    type=float,
    default=0.1,
    help="Threshold for significant change (default: 0.1 = 10%)",
)
@click.option("--export", type=click.Path(), help="Export comparison to file (CSV/Excel)")
def compare(**kwargs):
    """Compare benchmark runs"""
    console = Console()

    if kwargs["run_ids"] and kwargs["last"] != 2:
        console.print("[red]Error: Use either --run-ids or --last, not both[/red]")
        return

    if kwargs["run_ids"] is None:
        kwargs["run_ids"] = []

    storage = SQLiteStorage("results/benchmark_history.db")

    if kwargs["run_ids"]:
        run1_results = storage.custom_query(
            f"SELECT * FROM benchmarks WHERE id={kwargs['run_ids'][0]}"
        )
        run2_results = storage.custom_query(
            f"SELECT * FROM benchmarks WHERE id={kwargs['run_ids'][1]}"
        )

        if not run1_results or not run2_results:
            console.print("[red]Error: One or both run IDs not found[/red]")
            return

        comparison_data = Comparison.compare_runs(run1_results, run2_results, kwargs["threshold"])
    else:
        all_results = storage.get_history(kwargs["last"] * 2)
        if len(all_results) < 2:
            console.print("[red]Error: Not enough benchmark runs to compare[/red]")
            return

        midpoint = len(all_results) // 2
        run1_results = all_results[:midpoint]
        run2_results = all_results[midpoint : midpoint * 2]

        comparison_data = Comparison.compare_runs(run1_results, run2_results, kwargs["threshold"])

    console.print(Panel("Run Comparison", style="blue"))
    console.print(Comparison.format_comparison(comparison_data))

    if kwargs["statistics"]:
        stats1 = Statistics.calculate_basic(run1_results)
        stats2 = Statistics.calculate_basic(run2_results)
        console.print("\n" + Statistics.format_basic(stats1))
        console.print("\n" + Statistics.format_basic(stats2))

    if kwargs["export"]:
        console.print(f"\n[yellow]Exporting comparison to {kwargs['export']}...[/yellow]")


@main.command()
@click.option(
    "--test-type",
    "test_type",
    multiple=True,
    type=click.Choice(["randread", "randwrite", "read", "write", "randrw", "trim"]),
    help="Filter by test type",
)
@click.option(
    "--block-size",
    "block_size",
    multiple=True,
    type=click.Choice(["4k", "64k", "1M", "512k"]),
    help="Filter by block size",
)
@click.option("--detailed", is_flag=True, help="Show detailed statistics")
@click.option("--trends", is_flag=True, help="Show performance trends over time")
@click.option("--plots", is_flag=True, help="Generate visualization plots")
@click.option(
    "--plot-types",
    "plot_types",
    multiple=True,
    type=click.Choice(["bar", "scatter", "radar", "line"]),
    default=["bar", "scatter", "radar"],
    help="Plot types to generate",
)
@click.option(
    "--plot-output-dir", type=click.Path(), default="results/plots", help="Directory for plot files"
)
@click.option("--open-browser", is_flag=True, help="Open plots in browser after generation")
@click.option("--export", type=click.Path(), help="Export analysis to file")
def analyze(**kwargs):
    """Analyze historical benchmark data"""
    console = Console()

    storage = SQLiteStorage("results/benchmark_history.db")

    query = "SELECT * FROM benchmarks WHERE 1=1"
    params = []

    if kwargs["test_type"]:
        placeholders = ",".join(["?" for _ in kwargs["test_type"]])
        query += f" AND test_type IN ({placeholders})"
        params.extend(kwargs["test_type"])

    if kwargs["block_size"]:
        placeholders = ",".join(["?" for _ in kwargs["block_size"]])
        query += f" AND block_size IN ({placeholders})"
        params.extend(kwargs["block_size"])

    results = storage.custom_query(query, params if params else ())

    if not results:
        console.print("[yellow]No results found matching filters[/yellow]")
        return

    if kwargs["detailed"]:
        stats = Statistics.calculate_detailed(results)
        console.print(Statistics.format_detailed(stats))
    else:
        stats = Statistics.calculate_basic(results)
        console.print(Statistics.format_basic(stats))

    if kwargs["trends"]:
        console.print("\n[yellow]Trend analysis requires plot generation[/yellow]")
        if kwargs["plots"]:
            plotter = create_plotter(
                ["line"], results, {"plot_output_dir": kwargs["plot_output_dir"]}
            )
            plotter.generate()

    if kwargs["plots"]:
        plot_types = (
            list(kwargs["plot_types"]) if kwargs["plot_types"] else ["bar", "scatter", "radar"]
        )
        plotter = create_plotter(
            plot_types, results, {"plot_output_dir": kwargs["plot_output_dir"]}
        )
        plotter.generate()

        if kwargs["open_browser"]:
            from glob import glob

            for plot_file in glob(str(kwargs["plot_output_dir"]) + "/*.html"):
                console.print(f"[green]Opening {plot_file} in browser...[/green]")
                success = plotter.open_in_browser(plot_file)
                if not success:
                    console.print(f"[yellow]Browser open failed for {plot_file}[/yellow]")
                    console.print(f"[dim]File saved at: {plot_file}[/dim]")

        console.print(f"[green]Plots saved to {kwargs['plot_output_dir']}/[/green]")

    if kwargs["export"]:
        console.print(f"\n[yellow]Exporting analysis to {kwargs['export']}...[/yellow]")


@main.command()
@click.option(
    "--format",
    "format",
    type=click.Choice(["csv", "excel"]),
    default="excel",
    help="Export format",
)
@click.option("--output", type=click.Path(), required=True, help="Output file path")
@click.option("--after", type=str, help="Filter by date after YYYY-MM-DD")
@click.option("--before", type=str, help="Filter by date before YYYY-MM-DD")
@click.option(
    "--test-type",
    "test_type",
    multiple=True,
    type=click.Choice(["randread", "randwrite", "read", "write", "randrw", "trim"]),
    help="Filter by test type",
)
@click.option(
    "--block-size",
    "block_size",
    multiple=True,
    type=click.Choice(["4k", "64k", "1M", "512k"]),
    help="Filter by block size",
)
def export(**kwargs):
    """Export benchmark data to file"""
    console = Console()

    storage = SQLiteStorage("results/benchmark_history.db")

    query = "SELECT * FROM benchmarks WHERE 1=1"
    params = []

    if kwargs["after"]:
        query += " AND timestamp >= ?"
        params.append(kwargs["after"])

    if kwargs["before"]:
        query += " AND timestamp <= ?"
        params.append(kwargs["before"])

    if kwargs["test_type"]:
        placeholders = ",".join(["?" for _ in kwargs["test_type"]])
        query += f" AND test_type IN ({placeholders})"
        params.extend(kwargs["test_type"])

    if kwargs["block_size"]:
        placeholders = ",".join(["?" for _ in kwargs["block_size"]])
        query += f" AND block_size IN ({placeholders})"
        params.extend(kwargs["block_size"])

    results = storage.custom_query(query, params if params else ())

    if not results:
        console.print("[yellow]No results found matching filters[/yellow]")
        return

    console.print(f"[green]Exporting {len(results)} results to {kwargs['output']}...[/green]")

    if kwargs["format"] == "csv":
        formatter = CsvFormatter(kwargs["output"])
        formatter.format(results)
    else:
        formatter = ExcelFormatter(kwargs["output"])
        formatter.format(results)

    console.print("[green]Export complete[/green]")
