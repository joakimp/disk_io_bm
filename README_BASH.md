# Bash Implementation - fio_benchmark.sh

Lightweight bash-based disk I/O benchmarking tool using fio. Ideal for systems without Python.

## Overview

- Requires only `bash` and `fio`
- Text-based output with ASCII summary tables
- No external dependencies
- Automatic progress tracking

## Features

- **Test Modes**: test, lean (default), full, individual
- **Test Types**: randread, randwrite, read, write, randrw
- **Block Sizes**: 4k, 64k, 1M, 512k
- **Output**: Text files with formatted summary
- **Progress**: ASCII progress bar with elapsed/estimated time
- **Enhancements**: Direct I/O, latency tracking, mixed RandRW

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

No other dependencies required - just bash and fio!

## Usage

### Basic Execution

```bash
# Default: Lean mode (HDD, no concurrency)
./fio_benchmark.sh

# Quick test (15s runtime)
./fio_benchmark.sh --test

# Full mode with comprehensive tests
./fio_benchmark.sh --full
```

### Mode Options

**Preset modes:**

```bash
./fio_benchmark.sh              # Lean mode (HDD, no concurrency)
./fio_benchmark.sh --full      # Full mode
./fio_benchmark.sh --test      # Test mode (quick validation)
./fio_benchmark.sh --quick     # Quick mode (1G file, 15s runtime)
```

**Test type modifiers:**

```bash
./fio_benchmark.sh --ssd                           # Enable SSD-specific optimizations
./fio_benchmark.sh --concurrency                   # High concurrency mode
```

**Individual test flags** (mutually exclusive with --test and --full):

```bash
# Test types
./fio_benchmark.sh --randread     # Random read tests
./fio_benchmark.sh --randwrite    # Random write tests
./fio_benchmark.sh --read        # Sequential read tests
./fio_benchmark.sh --write       # Sequential write tests
./fio_benchmark.sh --randrw       # Mixed random read/write (70/30 split) tests

# Block sizes
./fio_benchmark.sh --4k           # 4k block size
./fio_benchmark.sh --64k          # 64k block size
./fio_benchmark.sh --1M           # 1M block size
./fio_benchmark.sh --512k         # 512k block size
```

### Individual Test Examples

```bash
# Run random read on 4k and 64k
./fio_benchmark.sh --randread --4k --64k

# Run sequential read and write on 1M
./fio_benchmark.sh --read --write --1M

# Run mixed random read/write tests on all block sizes
./fio_benchmark.sh --randrw --4k --64k --1M --512k

# Run multiple test types with concurrency
./fio_benchmark.sh --randread --randwrite --4k --64k --concurrency

# Quick test with custom file size
./fio_benchmark.sh --quick --filesize 500M --randread --4k

# Quick test with custom file size
./fio_benchmark.sh --quick --filesize 500M --randread --4k
```

### Custom Parameters

```bash
# Specify custom file size
./fio_benchmark.sh --filesize 20G     # 20G file size
./fio_benchmark.sh --filesize 500M    # 500M for fast testing
./fio_benchmark.sh --filesize 2T      # 2TB file size
```

## Mode Details

### Lean Mode (Default)

Runs original tests with enhancements:
- Tests: 3 block sizes (4k, 64k, 1M) × 4 core tests + randrw
- Runtime: 60s for randrw test
- Total: ~13 tests
- Duration: ~1-1.25 hours
- Includes: randrw (70/30 mix)

### Full Mode

Comprehensive testing:
- Tests: 4 block sizes (4k, 64k, 1M, 512k) × 4 core tests + randrw
- Runtime: 300s for randrw test
- Total: ~17 tests
- Duration: ~2-3 hours
- Includes: randrw (70/30 mix)

### Test Mode

Quick validation tests:
- Tests: 3 core tests (randread 4k, randwrite 64k, read 1M)
- Runtime: 15s per test
- Total: ~1 minute
- Purpose: Fast validation and testing

### Individual Test Mode

Run specific test types on selected block sizes:
- Combine any test types with any block sizes
- Requires at least one test type and one block size
- Useful for targeted performance analysis
- Creates separate output files: `bm_<type>_<size>_individual.txt`

## Notes

- Individual test flags must be combined with at least one block size flag
- Individual tests create separate output files: `bm_<type>_<size>_individual.txt`
- Progress bar is disabled in individual test mode; elapsed and estimated remaining time are shown
- Use `--quick` flag for fast testing (1G file, 15s runtime)
- Use `--filesize <size>` to specify custom file size

## Output

### Output Files

All results are saved to the `results/` directory:

- **`bm_*.txt`** - Detailed benchmark output per test type
- **`summary.txt`** - Aggregated summary of all tests
- **`*.bak`** - Timestamped backups of previous results
- **`bm_*_individual.txt`** - Individual test output files

### Output Format

After running tests, the script automatically generates a summary of core metrics:

```
Test          IOPS Read  IOPS Write  BW Read    BW Write   Lat Avg Read (us)  Lat Avg Write (us)  CPU                    I/O Time  Wall Time  Status
randread 4k   15000      N/A         58.5MB/s   N/A        50.0               N/A                 usr=10.0% sys=5.0%     35ms      10s        OK
randwrite 64k N/A        12000       N/A        46.7MB/s   N/A                70.0                usr=12.0% sys=6.0%     55ms      10s        OK
...

Test completed: 2025-12-31 00:34:01
Total I/O time: 108ms (actual disk I/O operations)
Total wall time: 30s (including setup/teardown)

Note: I/O Time = FIO disk operation duration. Wall Time = total elapsed time including file creation and cleanup.
```

**Time Columns:**
- **I/O Time**: Actual FIO disk I/O operation duration (may be very short for fast disks with small files)
- **Wall Time**: Total elapsed wall-clock time including file creation, FIO execution, and cleanup

The summary is displayed on the console and saved to `results/summary.txt`.

## Progress Tracking

The script displays dynamic progress updates during execution:
- ASCII progress bar
- Current test name
- Elapsed time (HH:MM:SS)
- Estimated remaining time
- Updates occur every ~10 seconds

Note: In some terminals (e.g., iTerm2), intermediate progress updates may appear in scrollback history after tests complete. This is expected behavior—the progress line is properly overwritten during execution and cleared when all tests finish.

## Advantages

- **No Python dependency**: Works on systems with minimal setup
- **Fast execution**: Minimal overhead, direct bash scripting
- **Simple**: Easy to understand and modify
- **Portable**: Works on any system with bash and fio

## Limitations

- Text-only output (no JSON/CSV)
- No persistent database (text files only)
- No built-in plot generation
- Manual history review (no querying)
- ASCII tables only (no rich formatting)

## Comparison with Python Version

The Python version ([README_PYTHON.md](README_PYTHON.md)) adds:
- Rich terminal output with tables and colors
- Multiple output formats (table, JSON, CSV)
- SQLite database for persistent storage
- Queryable benchmark history (last N runs, custom SQL)
- Plot generation (bar, line, box, etc.)
- Better error handling and test validation
- macOS psync engine support for reliability
