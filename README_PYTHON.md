# Python Implementation - disk-benchmark-py

Feature-rich Python disk I/O benchmarking tool using fio. Extensible with multiple storage backends and visualization capabilities.

## Overview

- Requires Python 3.10+ and `uv` for dependency management
- Rich terminal output with progress bars and colored tables
- SQLite database for persistent benchmark history
- Multiple output formats: table, JSON, CSV
- macOS support with automatic psync engine
- Extensible Python codebase

## Features

- **Test Modes**: test, lean (default), full, individual
- **Test Types**: randread, randwrite, read, write, randrw, trim
- **Block Sizes**: 4k, 64k, 1M, 512k
- **Flags**: --ssd, --hdd, --concurrency, --quick, --filesize
- **Output Formats**: table (default), json, csv, excel
- **Storage Backends**: SQLite (default), JSON, CSV, none
- **Plot Generation**: Interactive Plotly plots (bar, scatter, radar, line)
- **History**: Query last N benchmark runs
- **Custom Queries**: Execute SQL queries on benchmark database
- **Analytics**: Statistical analysis and run comparison
- **Progress**: Rich progress bars with current test, elapsed time, estimated remaining
- **Error Handling**: Graceful handling of FIO failures, timeouts, TRIM warnings

## Installation

### Prerequisites

Install `fio` if not already installed:

**macOS:**
```bash
brew install fio
```

**Linux:**
```bash
# Debian/Ubuntu
sudo apt-get install fio

# RHEL/CentOS
sudo yum install fio
```

### Python Setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository and install dependencies
cd /path/to/disk_io_bm
uv sync
```

## Usage

### Quick Start

```bash
# Quick test (15s runtime)
uv run disk-benchmark-py test

# Lean mode (default)
uv run disk-benchmark-py run

# Full mode
uv run disk-benchmark-py run --mode full

# View recent history
uv run disk-benchmark-py run --history 10
```

### Commands

#### Main Command: `disk-benchmark-py run`

**Test Modes:**
```bash
# Test mode (quick validation)
uv run disk-benchmark-py run --mode test

# Lean mode (default - matches bash default)
uv run disk-benchmark-py run --mode lean

# Full mode (comprehensive testing)
uv run disk-benchmark-py run --mode full

# Individual mode (custom tests)
uv run disk-benchmark-py run --mode individual
```

**Test Type Modifiers:**
```bash
# Enable SSD-specific tests (trim)
uv run disk-benchmark-py run --ssd

# Enable HDD-specific tests
uv run disk-benchmark-py run --hdd

# Enable high concurrency
uv run disk-benchmark-py run --concurrency

# Quick mode (1G file, 15s runtime)
uv run disk-benchmark-py run --quick

# Combine flags
uv run disk-benchmark-py run --mode full --ssd --concurrency
```

**Individual Test Types:**
```bash
# Test types
uv run disk-benchmark-py run --test-type randread --test-type randwrite --test-type read --test-type write --test-type randrw --test-type trim

# Block sizes
uv run disk-benchmark-py run --block-size 4k --block-size 64k --block-size 1M --block-size 512k

# Individual mode example
uv run disk-benchmark-py run --mode individual --test-type randread --block-size 4k --block-size 64k
```

**Output Formats:**
```bash
# Table output (default - Rich formatted)
uv run disk-benchmark-py run --output-format table

# JSON output
uv run disk-benchmark-py run --output-format json

# CSV output
uv run disk-benchmark-py run --output-format csv
```

**Storage Backends:**
```bash
# SQLite (default - persistent database)
uv run disk-benchmark-py run --database sqlite

# JSON files (timestamped)
uv run disk-benchmark-py run --database json

# No storage (in-memory only)
uv run disk-benchmark-py run --no-database
```

**History & Queries:**
```bash
# View last 10 runs
uv run disk-benchmark-py run --history 10

# View last 5 runs
uv run disk-benchmark-py run --history 5

# Custom SQL query
uv run disk-benchmark-py run --query-sql "SELECT * FROM benchmarks WHERE test_type='read' ORDER BY timestamp DESC LIMIT 5"

# Query by specific parameters
uv run disk-benchmark-py run --query-sql "SELECT test_type, block_size, AVG(read_iops) as avg_iops FROM benchmarks GROUP BY test_type, block_size"
```

**Plot Generation:**
```bash
# Generate plots after benchmark
uv run disk-benchmark-py run --plots

# Generate specific plot types
uv run disk-benchmark-py run --plots --plot-types bar,scatter

# Generate plots and open in browser
uv run disk-benchmark-py run --plots --open-browser

# Generate plots with custom output directory
uv run disk-benchmark-py run --plots --plot-output-dir /custom/plots
```

**Excel Export:**
```bash
# Export to Excel
uv run disk-benchmark-py run --output-format excel --output results.xlsx
```

**Advanced Options:**
```bash
# Custom runtime
uv run disk-benchmark-py run --runtime 600

# Custom file size
uv run disk-benchmark-py run --filesize 20G

# Custom database path
uv run disk-benchmark-py run --db-path /custom/path/benchmark.db

# JSON output directory
uv run disk-benchmark-py run --output-format json --json-output-dir /custom/json/dir
```

#### Test Command: `disk-benchmark-py test`

Quick validation mode:

```bash
# Quick test (default)
uv run disk-benchmark-py test

# Quick test with specific mode
uv run disk-benchmark-py test --mode lean

# Quick test with SSD
uv run disk-benchmark-py test --ssd

# Quick test with concurrency
uv run disk-benchmark-py test --concurrency
```

## Mode Details

### Test Mode

Quick validation tests:
- Tests: 3 (randread 4k, randwrite 64k, read 1M)
- Runtime: 15s per test
- Purpose: Fast validation
- Duration: ~1 minute

### Lean Mode (Default)

Original tests with enhancements:
- Tests: 14 tests
  - 4 block sizes (4k, 64k, 1M) × 4 core tests
  - Plus randrw (4k, 60s)
  - Optional trim (4k, with --ssd)
- Runtime: 60s for core tests, 300s for randrw
- Duration: ~1-1.25 hours
- Includes: Direct I/O, latency tracking

### Full Mode

Comprehensive testing:
- Tests: 18 tests
  - 4 block sizes (4k, 64k, 1M, 512k) × 4 core tests
  - Plus randrw (4k, 60s)
  - Optional trim (4k, with --ssd)
- Runtime: 300s for all tests
- Duration: ~2-3 hours
- Comprehensive coverage of all test types and block sizes

### Individual Test Mode

Run specific test types on selected block sizes:
- Combine any test types with any block sizes
- Requires at least one test type and one block size
- Useful for targeted performance analysis
- Creates separate test entries

## Output

### Directory Structure

Both tools save results to `results/` directory:

### Bash Output

- **`bm_*.txt`** - Raw FIO output for each test type
- **`summary.txt`** - Formatted ASCII table with all results
- **`*.bak`** - Timestamped backups of previous results
- **`bm_*_individual.txt`** - Individual test output files

### Python Output

- **`benchmark_history.db`** - SQLite database with all benchmark results
- **`results/json/`** - Individual JSON files for each run
- **`results/*.json`** - Aggregated JSON exports
- **Console** - Rich-formatted tables and progress bars

### Output Formats

**Table Output (default):**
```
Disk I/O Benchmark Results
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Test          ┃ IOPS Read ┃ IOPS Write ┃ BW Read     ┃ BW Write    ┃ Lat Avg Read (us) ┃ Lat Avg Write (us) ┃ CPU                   ┃ Runtime ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ randread 4k   │ 11800.0   │ N/A        │ 46.0MiB/s   │ N/A         │ 84.66             │ N/A                │ usr=0.69%, sys=8.50%  │ 15.0s   │
│ randwrite 64k │ N/A       │ 29600.0    │ N/A         │ 1852.0MiB/s │ N/A               │ 32.72              │ usr=3.62%, sys=27.36% │ 0.6s    │
│ read 1M       │ 2270.0    │ N/A        │ 2271.0MiB/s │ N/A         │ 439.24            │ N/A                │ usr=0.00%, sys=6.00%  │ 0.5s    │
└───────────────┴───────────┴────────────┴─────────────┴─────────────┴───────────────────┴────────────────────┴───────────────────────┴─────────┘

```


**JSON Output:**
```json
[
  {
    "test_type": "randread",
    "block_size": "4k",
    "read_iops": 15000,
    "write_iops": 0,
    "read_bw": 61440000,
    "write_bw": 0,
    "read_latency_us": 50.0,
    "write_latency_us": 0,
    "cpu": "usr=10.0%, sys=5.0%",
    "runtime_sec": 15.00,
    "status": "OK"
  },
  ...
]
```

**CSV Output:**
```csv
Test Type,Block Size,Read IOPS,Write IOPS,Read MB/s,Write MB/s,Read Lat (us),Write Lat (us),CPU,Runtime (s),Status
randread,4k,15000,0,58.50,0.00,50.00,0,usr=10.0% sys=5.0%,15.00,OK
...
```

### Compare Runs

Compare benchmark runs to identify performance changes:

```bash
# Compare last 2 runs (default)
disk-benchmark-py compare

# Compare last 5 runs with statistics
disk-benchmark-py compare --last 5 --statistics

# Compare specific runs with threshold 20%
disk-benchmark-py compare --run-ids 42 43 --threshold 0.2

# Compare and export to Excel
disk-benchmark-py compare --last 3 --export comparison.xlsx

# Compare with plots
disk-benchmark-py compare --last 2 --plots
```

**Comparison Features:**
- Side-by-side table with deltas and percentages
- Configurable threshold for significant changes (default: 10%)
- Optional statistical analysis
- Optional comparison plots
- Export to CSV/Excel

### Analyze History

Analyze historical benchmark data:

```bash
# Overall statistics
disk-benchmark-py analyze

# Detailed statistics for randread
disk-benchmark-py analyze --test-type randread --detailed

# Statistics with trends and plots
disk-benchmark-py analyze --trends --plots

# Filter by block size and export
disk-benchmark-py analyze --block-size 4k 64k --export analysis.xlsx
```

**Analysis Features:**
- Basic statistics: mean, median, min, max per metric
- Detailed statistics: add std dev, percentiles, count
- Filter by test type and block size
- Optional trend analysis over time
- Generate visualization plots
- Export to CSV/Excel

### Export Data

Export benchmark data to various formats:

```bash
# Export all data to Excel
disk-benchmark-py export --format excel --output all_results.xlsx

# Export CSV for date range
disk-benchmark-py export --format csv --output recent.csv --after 2024-01-01

# Filter by test type and export
disk-benchmark-py export --format excel --output randread.xlsx --test-type randread

# Export with date filters
disk-benchmark-py export --format excel --output 2024_results.xlsx --after 2024-01-01 --before 2024-12-31
```

**Export Features:**
- Formats: CSV, Excel
- Excel organized by metrics (Summary, IOPS, Bandwidth, Latency, Raw)
- ISO date format support (YYYY-MM-DD)
- Filter by date range, test type, block size
- Multiple sheets for easy navigation

## Development

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_config.py -v

# Run tests with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Run tests quietly
uv run pytest tests/ -q
```

### Code Quality

```bash
# Linting
uv run ruff check cli.py src/

# Auto-fix linting issues
uv run ruff check --fix cli.py src/

# Type checking
uv run mypy cli.py --config-file=pyproject.toml

# Type checking specific files
uv run mypy src/config.py src/executor.py --config-file=pyproject.toml
```

## Database Schema

The SQLite database uses the following schema:

```sql
CREATE TABLE benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    mode TEXT,
    filesize TEXT,
    runtime INTEGER,
    test_type TEXT,
    block_size TEXT,
    read_iops REAL,
    write_iops REAL,
    read_bw REAL,
    write_bw REAL,
    read_latency_us REAL,
    write_latency_us REAL,
    cpu TEXT,
    status TEXT,
    runtime_sec REAL,
    metadata TEXT
);

CREATE INDEX idx_timestamp ON benchmarks(timestamp);
CREATE INDEX idx_test_type ON benchmarks(test_type);
```

## Example Queries

```bash
# Get most recent runs
uv run disk-benchmark-py run --history 10

# Get best random read performance
uv run disk-benchmark-py run --query-sql "SELECT test_type, block_size, MAX(read_iops) as max_iops FROM benchmarks WHERE test_type='randread' GROUP BY test_type, block_size ORDER BY max_iops DESC LIMIT 5"

# Get average performance by test type
uv run disk-benchmark-py run --query-sql "SELECT test_type, AVG(read_iops) as avg_iops, AVG(read_bw) as avg_bw FROM benchmarks GROUP BY test_type ORDER BY avg_iops DESC"

# Compare two runs
uv run disk-benchmark-py run --query-sql "SELECT * FROM benchmarks WHERE timestamp > datetime('now', '-7 days') ORDER BY timestamp DESC LIMIT 20"

# Find slowest tests
uv run disk-benchmark-py run --query-sql "SELECT test_type, block_size, runtime_sec FROM benchmarks ORDER BY runtime_sec DESC LIMIT 10"
```

## macOS Support

The Python tool automatically detects macOS and adjusts FIO parameters:

- **IO Engine**: Uses `--ioengine=psync` on macOS
- **I/O Depth**: Sets `--iodepth=1` on macOS
- **Num Jobs**: Sets `--numjobs=1` on macOS
- **Direct I/O**: Disabled on macOS (psync doesn't support it)
- **Concurrency**: Disabled on macOS

This ensures reliable operation on macOS systems where fio behaves differently.

## Advantages over Bash

- **Rich terminal output**: Colorful tables, progress bars
- **Persistent storage**: SQLite database for historical analysis
- **Queryable history**: SQL queries to find patterns, compare runs
- **Multiple output formats**: Table, JSON, CSV for different use cases
- **Better error handling**: Graceful degradation, detailed error messages
- **Extensible**: Easy to add new features, plot generation, etc.
- **Type safety**: mypy type checking
- **Code quality**: ruff linting, test coverage

## Troubleshooting

### FIO Issues

**macOS shared memory error:**
```
error: failed to setup shm segment
```

**Solution**: The Python tool detects macOS and uses the psync engine, avoiding this issue.

**TRIM on regular files:**
```
WARNING: TRIM test requires a block device, not a regular file.
SKIPPED: TRIM requires block device, not regular file (file_path)
```

This is expected behavior. TRIM only works on block devices.

### Testing Issues

**Mock data in tests:**
Tests use mocked FIO output for speed and reliability. Real FIO execution happens during actual benchmark runs.

**Missing fio:**
```bash
# Test if fio is available
which fio

# On macOS:
brew install fio
```

## Comparison with Bash

| Feature | Bash | Python |
|---------|-------|--------|
| Test Modes | test, lean, full, individual | Same |
| Test Types | 6 types | Same |
| Block Sizes | 4 sizes | Same |
| Flags | --ssd, --hdd, --concurrency, --quick, --filesize | Same |
| Progress | ASCII bar | Rich progress bars |
| Output | Text + ASCII table | Table/JSON/CSV |
| Storage | Text files only | SQLite database + JSON + CSV files |
| History | Manual file review | Queryable history (SQL) |
| Plot Generation | N/A | Interactive Plotly plots |
| Analytics | N/A | Statistics and comparison |
| Error Handling | Basic | Detailed messages |
| macOS Support | Yes | (with psync engine) |
| Extensibility | Hard | Easy to extend |
| Dependencies | bash, fio | Python 3.10+, uv, fio |
| Dependencies | bash, fio | Python 3.10+, uv, fio |

## Project Structure

```
disk_io_bm/
├── pyproject.toml           # UV dependency management
├── cli.py                  # Click-based CLI (disk-benchmark-py)
├── src/
│   ├── __init__.py
│   ├── config.py         # Configuration (BenchmarkConfig, Mode, StorageBackend)
│   ├── executor.py       # FIO test execution with JSON parsing
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── sqlite.py  # SQLite storage backend
│   │   ├── json.py   # JSON file storage
│   │   └── csv_storage.py  # CSV file storage
│   ├── formatters/
│   │   ├── __init__.py
│   │   ├── table.py  # Rich table formatter
│   │   ├── json.py   # JSON formatter
│   │   └── csv_formatter.py  # CSV and Excel formatters
│   ├── plots/
│   │   ├── __init__.py
│   │   ├── base.py   # Abstract base plotter
│   │   └── plotly.py  # Interactive Plotly plots
│   └── analytics/
│       ├── __init__.py
│       ├── statistics.py  # Basic and detailed statistics
│       └── comparison.py  # Run comparison logic
├── tests/
│   ├── __init__.py
│   ├── test_config.py  # Configuration tests
│   ├── test_executor.py  # Executor tests (mocked FIO output)
│   ├── test_formatters.py # Formatter tests
│   ├── test_storage.py  # Storage tests
│   ├── test_plots.py    # Plot tests
│   └── test_analytics.py # Analytics tests
├── fio_benchmark.sh        # Bash implementation
├── README.md               # Main entry point
├── README_BASH.md          # Bash documentation
└── README_PYTHON.md         # Python documentation (this file)
```
