
# Benchmarking file I/O

This script benchmarks disk I/O performance using the fio tool, supporting various test modes and configurations.

Details are discussed in a blog post: [ZFS performance tuning](https://martin.heiland.io/2018/02/23/zfs-tuning/index.html)

Originally, four tests are run for the block sizes {4k, 64k, 1M}: random read, random write, sequential read, and sequential write. The script has been enhanced with additional modes for comprehensive evaluation.

## Enhanced Features

The script now includes additional lean tests for more comprehensive disk performance evaluation:

- **Direct I/O**: All tests bypass the OS cache for raw disk performance.
- **Latency Tracking**: Added to 4k random read and 1M sequential read tests to measure response times.
- **Mixed Random Read/Write**: A new test with 70% read / 30% write at 4k block size, run for 60 seconds.
- **Trim Test**: For SSDs only (enabled with --ssd flag), tests garbage collection at 4k block size.
- **High Concurrency**: Optional (enabled with --concurrency flag), increases jobs to 4 and I/O depth to 16 on the 64k random read test.

## Usage

The script supports lean, full, test, and individual test modes:

- **Lean Mode (Default)**: Runs the original tests with enhancements (direct I/O, latency, mixed RandRW, optional trim/concurrency). Lean tests use shorter runtimes (60s) for efficiency. Total runtime ~1-1.25 hours.
- **Full Mode**: Adds comprehensive tests with full runtimes (300s for lean additions) and extra block sizes (512k). Total runtime ~2-3 hours.
- **Test Mode**: Runs partial core tests (4k randread, 64k randwrite, 1M read) with 15s runtime for quick validation. Total runtime ~1 minute.
- **Individual Test Mode**: Run specific test types on selected block sizes. Useful for targeted performance analysis.

Run the script with optional flags:

**Preset modes:**
- `bash fio_benchmark.sh`: Lean mode (HDD, no concurrency).
- `bash fio_benchmark.sh --full`: Full mode with additional tests.
- `bash fio_benchmark.sh --test`: Test mode (15s runtime, partial core tests for quick validation).

**Test type modifiers:**
- `bash fio_benchmark.sh --ssd`: Enable SSD-specific tests (e.g., trim).
- `bash fio_benchmark.sh --concurrency`: Enable high concurrency on select tests.
- `bash fio_benchmark.sh --full --ssd --concurrency`: Combine for comprehensive SSD testing.

**Individual test flags (mutually exclusive with --test and --full):**

Test types:
- `--randread`: Random read tests
- `--randwrite`: Random write tests
- `--read`: Sequential read tests
- `--write`: Sequential write tests
- `--randrw`: Mixed random read/write (70/30 split) tests
- `--trim`: Trim tests (requires --ssd)

Block sizes:
- `--4k`: Run tests with 4k block size
- `--64k`: Run tests with 64k block size
- `--1M`: Run tests with 1M block size
- `--512k`: Run tests with 512k block size

**Individual test examples:**
```bash
# Run random read on 4k and 64k
bash fio_benchmark.sh --randread --4k --64k

# Run sequential read and write on 1M
bash fio_benchmark.sh --read --write --1M

# Run mixed random read/write tests on all block sizes
bash fio_benchmark.sh --randrw --4k --64k --1M --512k

# Run trim test with SSD flag
bash fio_benchmark.sh --trim --4k --ssd

# Run multiple test types with concurrency
bash fio_benchmark.sh --randread --randwrite --4k --64k --concurrency
```

**Notes:**
- Individual test flags must be combined with at least one block size flag
- Trim tests only support 4k block size
- Individual tests create separate output files: `bm_<type>_<size>_individual.txt`
- Progress bar is disabled in individual test mode; elapsed and estimated remaining time are shown

**Note**: On macOS, ensure `fio` is installed (e.g., via Homebrew). Summary parsing is optimized for macOS fio output; use `--test` for quick checks.

The script displays dynamic progress updates during execution, including an ASCII progress bar, current test name, elapsed time (HH:MM:SS), and estimated remaining time. Updates occur every ~10 seconds.

Note: In some terminals (e.g., iTerm2), intermediate progress updates may appear in the scrollback history after tests complete. This is expected behavior—the progress line is properly overwritten during execution and cleared when all tests finish.

Results are saved to bm_*.txt files.

## Summary Output

After running tests, the script automatically generates a summary of core metrics (IOPS, bandwidth, latency, CPU) in a table format. The summary is displayed on the console and saved to `summary.txt`. If the `column` tool is installed, the table is aligned; otherwise, a basic format is used.

Example output:
```
Test          IOPS Read  IOPS Write  BW Read    BW Write   Lat Avg Read (us)  Lat Avg Write (us)  CPU
randread 4k   15000      N/A         58.5MB/s   N/A        50.0               N/A                 usr=10.0% sys=5.0%
randwrite 64k N/A        12000       N/A        46.7MB/s   N/A                70.0               usr=12.0% sys=6.0%
...
```
