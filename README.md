# Disk I/O Benchmarking Tools

Collection of disk I/O benchmarking tools for Linux and macOS using fio.

## Tools

- **[Bash Implementation](README_BASH.md)** - `fio_benchmark.sh`
  - Lightweight, requires only bash and fio
  - Ideal for systems without Python
  - Text output, ASCII summary tables

- **[Python Implementation](README_PYTHON.md)** - `disk-benchmark-py`
  - Feature-rich, extensible Python implementation
  - Multiple storage backends (SQLite, JSON)
  - Rich terminal output with tables and colors
  - Queryable benchmark history

## Quick Start

### Bash (Minimal Requirements)

```bash
./fio_benchmark.sh --test
```

### Python (Full Features)

```bash
# Install dependencies
uv sync

# Run benchmark
uv run disk-benchmark-py run --mode test
```

## Feature Comparison

| Feature | Bash | Python |
|---------|-------|--------|
| Test Modes | test, lean, full, individual | Same |
| Test Types | 6 types (randread, randwrite, read, write, randrw, trim) | Same |
| Block Sizes | 4 sizes (4k, 64k, 1M, 512k) | Same |
| Progress | ASCII bar | Rich progress bars |
| Output | Text + ASCII table | Table/JSON/CSV formats |
| Storage | Text files only | SQLite database + JSON files |
| History | Manual file review | Queryable history (last N runs, custom SQL) |
| Error Handling | Basic | Detailed messages |
| macOS Support | | (with psync engine) |
| Dependencies | bash, fio | Python 3.10+, uv, fio |
| Extensibility | Hard | Easy to extend |

## Installation

### Prerequisites

Both tools require `fio` to be installed on your system:

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

### Python Tool Setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository and install dependencies
cd /path/to/disk_io_bm
uv sync
```

## Usage Examples

### Bash Tool

```bash
# Quick test
./fio_benchmark.sh --test

# Full mode with SSD tests
./fio_benchmark.sh --full --ssd --concurrency

# Individual tests
./fio_benchmark.sh --randread --4k --64k --1M --concurrency

# Quick test with custom file size
./fio_benchmark.sh --quick --filesize 500M --randread --4k
```

### Python Tool

```bash
# Quick test
uv run disk-benchmark-py test

# Lean mode (default)
uv run disk-benchmark-py run

# Full mode with SQLite storage
uv run disk-benchmark-py run --mode full --database sqlite

# View recent history
uv run disk-benchmark-py run --history 10

# Custom SQL query
uv run disk-benchmark-py run --query-sql "SELECT * FROM benchmarks WHERE test_type='read' ORDER BY timestamp DESC LIMIT 5"

# JSON output
uv run disk-benchmark-py run --output-format json
```

## Output

Both tools save results to `results/` directory:

### Bash Output
- `bm_*.txt` - Raw FIO output per test
- `summary.txt` - Formatted ASCII table
- `*.bak` - Timestamped backups

### Python Output
- `benchmark_history.db` - SQLite database
- `results/json/` - Individual JSON files
- `results/*.json` - Aggregated JSON exports
- Console - Rich-formatted tables

## Development

### Python Tool

```bash
# Run tests
uv run pytest tests/ -v

# Run linting
uv run ruff check cli.py src/

# Run type checking
uv run mypy cli.py --config-file=pyproject.toml
```

## Choosing Between Tools

### Use Bash (`fio_benchmark.sh`) when:
- System has no Python 3.10+ installed
- Need minimal dependencies
- Want simple, portable tool
- Quick one-time benchmarks

### Use Python (`disk-benchmark-py`) when:
- Want rich, formatted output
- Need historical data analysis
- Want to query and compare benchmark results
- Need multiple output formats (JSON, CSV)
- Running regular benchmarks over time
- Want to extend functionality with custom features
- On macOS (automatic psync engine support)

## License

This project is provided as-is for disk I/O benchmarking purposes.
