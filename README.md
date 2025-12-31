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
| Test Types | 5 types (randread, randwrite, read, write, randrw) | Same |
| Block Sizes | 4 sizes (4k, 64k, 1M, 512k) | Same |
| Progress | ASCII bar | Rich progress bars |
| Output | Text + ASCII table | Table/JSON/CSV formats |
| Storage | Text files only | SQLite database + JSON files |
| History | Manual file review | Queryable history (last N runs, custom SQL) |
| Error Handling | Basic | Detailed messages |
| macOS Support | Yes | (with psync engine) |
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

### Storage Backends

```bash
# SQLite (default - persistent database)
# If no --database flag is specified, SQLite is used automatically
uv run disk-benchmark-py run

# Explicitly use SQLite
uv run disk-benchmark-py run --database sqlite

# JSON files (timestamped)
uv run disk-benchmark-py run --database json

# No storage (in-memory only)
uv run disk-benchmark-py run --no-database
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

## Benchmarking Considerations

When running disk I/O benchmarks, several factors affect the accuracy and reliability of your results. Understanding these helps you choose appropriate test parameters and interpret results correctly.

### File Size and Caching Effects

The test file size is one of the most critical parameters affecting benchmark accuracy.

**Caching layers that can skew results:**

| Cache Type | Typical Size | Impact |
|------------|--------------|--------|
| OS Page Cache (RAM) | All available RAM | Read tests may measure memory speed instead of disk |
| SSD DRAM Cache | 256MB - 2GB | Hot data served from fast DRAM |
| SSD SLC Cache | 10GB - 100GB+ | Burst writes 2-5x faster than sustained |
| HDD Buffer | 64MB - 256MB | Small sequential operations cached |

**Recommendations by use case:**

| Scenario | Recommended File Size | Notes |
|----------|----------------------|-------|
| Quick validation | 1GB | Just verify the tool works |
| Typical benchmarking | 2x RAM or 10GB minimum | Minimizes page cache effects |
| Enterprise/datacenter | 2x RAM or 50GB+ | More representative of production |
| NVMe SSD testing | Larger than SLC cache + 2x RAM | Measures sustained, not burst performance |

**This tool's defaults:**
- `--mode test`: 1GB file, 15s runtime - Quick validation only
- `--mode lean/full`: 10GB file, 300s runtime - Suitable for systems with ≤4GB RAM

For systems with more RAM, consider using `--filesize 20G` or larger to ensure you're measuring actual disk performance rather than cache performance.

### Impact on Statistics

| Aspect | Smaller File (cached) | Larger File (uncached) |
|--------|----------------------|------------------------|
| **Mean IOPS/bandwidth** | Inflated (cache hits) | Representative of sustained performance |
| **Variance** | Artificially low | Higher, reflects real-world variability |
| **Confidence intervals** | Narrower but misleading | Wider but accurate |
| **Reproducibility** | High but not meaningful | May vary between runs |

### SSD-Specific Considerations

Modern SSDs have complex performance characteristics:

- **SLC Cache**: Consumer SSDs often write to fast pseudo-SLC cache first, then migrate to slower TLC/QLC. Small file tests may complete entirely within SLC cache, showing 2-5x inflated write speeds.
- **Garbage Collection**: Small tests may not trigger GC cycles, hiding performance degradation that occurs in real workloads.
- **Thermal Throttling**: Short tests may not reveal throttling that occurs during sustained operations.

### When Smaller Files Are Acceptable

- Quick validation that fio and the benchmark tool are working
- Comparing relative performance between configurations (if both use same parameters)
- Testing workloads that genuinely operate on small files
- Reducing SSD wear during repeated testing
- CI/CD pipeline smoke tests

### Runtime Duration

The `--runtime` parameter also affects result quality:

- **15 seconds**: Minimum for quick tests; high variance between runs
- **60 seconds**: Reasonable for most comparisons
- **300 seconds** (default): Good balance of accuracy and time
- **600+ seconds**: Better for detecting thermal throttling and GC effects

### General Best Practices

1. **Consistent parameters**: When comparing results, always use identical file size, runtime, and block sizes
2. **Multiple runs**: Run benchmarks 2-3 times to verify consistency
3. **Idle system**: Close unnecessary applications to reduce interference
4. **Fresh state**: For SSDs, consider running a TRIM operation before benchmarking
5. **Temperature**: Allow drives to cool between intensive test runs

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
