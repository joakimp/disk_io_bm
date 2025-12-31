"""CLI with auto-detection for disk I/O benchmarking"""

import click
from src.config import BenchmarkConfig, StorageBackend


@click.group()
def disk_benchmark():
    """Disk I/O benchmarking tool"""
    pass


@disk_benchmark.command()
@click.option(
    "--mode",
    type=click.Choice(["test", "lean", "full", "individual"]),
    help="Test mode (auto-detected if not specified)",
)
@click.option("--ssd", is_flag=True, help="Enable SSD-specific tests")
@click.option("--concurrency", is_flag=True, help="High concurrency mode")
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
@click.option(
    "--timeout",
    type=int,
    default=0,
    help="Timeout per test in seconds (0=auto-calculate based on filesize)",
)
@click.option("--filesize", type=str, default="10G", help="File size for fio")
@click.option("--output-dir", type=click.Path, default="results", help="Output directory")
@click.option(
    "--output-format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format (table/json/csv)",
)
@click.option(
    "--json-output-dir",
    type=click.Path,
    default="results/json",
    help="Directory for JSON output files (individual tests)",
)
@click.option(
    "--database",
    type=click.Choice(["none", "sqlite"]),
    default="sqlite",
    help="Storage backend (none/sqlite)",
)
@click.option(
    "--db-path",
    type=click.Path,
    default="results/benchmark_history.db",
    help="Path to SQLite database file",
)
@click.option("--plots", is_flag=True, help="Generate plots")
@click.option(
    "--plot-types",
    "plot_types",
    multiple=True,
    type=click.Choice(["bar", "line", "heatmap", "scatter", "box", "radar"]),
    default=["bar"],
    help="Plot types to generate",
)
@click.option(
    "--plot-output-dir",
    type=click.Path,
    default="results/plots",
    help="Directory for plot files",
)
@click.option("--interactive-plots", is_flag=True, help="Open plots in browser")
@click.option("--history", type=int, default=10, help="Show N recent benchmark runs")
@click.pass_context
def main(
    ctx,
    mode,
    ssd,
    concurrency,
    test_type,
    block_size,
    runtime,
    timeout,
    filesize,
    output_dir,
    output_format,
    json_output_dir,
    database,
    db_path,
    plots,
    plot_types,
    plot_output_dir,
    interactive_plots,
    history,
):
    """Run disk I/O benchmarks with fio"""
    import time

    from src.executor import BenchmarkExecutor
    from src.storage import SQLiteStorage, JsonStorage
    from src.formatters import TableFormatter, JsonFormatter
    from rich.console import Console

    console = Console()

    # Create configuration
    config = BenchmarkConfig(
        mode=mode,
        ssd=ssd,
        concurrency=concurrency,
        test_types=list(test_type),
        block_sizes=list(block_size),
        runtime=runtime,
        timeout=timeout,
        filesize=filesize,
        results_dir=output_dir,
        output_format=output_format,
        json_output_dir=json_output_dir,
        generate_plots=plots,
        plot_types=list(plot_types),
        plot_output_dir=plot_output_dir,
        interactive_plots=interactive_plots,
    )

    # Override database config
    if database == "none":
        database_backend = StorageBackend.NONE
    else:
        database_backend = StorageBackend.SQLITE

    # Run benchmarks and track total time
    start_time = time.time()
    executor = BenchmarkExecutor(config)
    results = executor.run_all_tests()
    total_wall_time = time.time() - start_time

    # Store results
    if database_backend != StorageBackend.NONE:
        if database_backend == StorageBackend.SQLITE:
            storage = SQLiteStorage(db_path)
        else:
            storage = JsonStorage(output_dir)
        storage.save_results(results, config)
    else:
        # In-memory for no database
        pass

    # Format and display output
    if output_format == "table":
        formatter = TableFormatter()
        formatter.format(results)
    elif output_format == "json":
        formatter = JsonFormatter(json_output_dir)
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
    if plots and results:
        from src.plots import PlotlyPlotter

        plot_config = {
            "plot_types": list(plot_types),
            "plot_output_dir": plot_output_dir,
        }
        plotter = PlotlyPlotter(results, plot_config)
        plotter.generate()
        console.print(f"Plots saved to {plot_output_dir}/")

        if interactive_plots:
            # Open the first generated plot in browser
            from pathlib import Path

            plot_dir = Path(plot_output_dir)
            html_files = list(plot_dir.glob("*.html"))
            if html_files:
                plotter.open_in_browser(str(html_files[0]))

    console.print("Benchmark completed!")
    console.print(f"Results saved to {output_dir}/")
