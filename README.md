
# Benchmarking file I/O

This script test disk i/o performance using the tool fio.

Details are discussed in a blog post: [ZFS performance tuning](https://martin.heiland.io/2018/02/23/zfs-tuning/index.html)

In short, four tests are run for the block sizes {4k, 64k, 1M}. The four tests are random read, random write, sequential read, and sequential write.

## Enhanced Features

The script now includes additional lean tests for more comprehensive disk performance evaluation:

- **Direct I/O**: All tests bypass the OS cache for raw disk performance.
- **Latency Tracking**: Added to 4k random read and 1M sequential read tests to measure response times.
- **Mixed Random Read/Write**: A new test with 70% read / 30% write at 4k block size, run for 60 seconds.
- **Trim Test**: For SSDs only (enabled with --ssd flag), tests garbage collection at 4k block size.
- **High Concurrency**: Optional (enabled with --concurrency flag), increases jobs to 4 and I/O depth to 16 on the 64k random read test.

## Usage

The script supports lean, full, and test modes:

- **Lean Mode (Default)**: Runs the original tests with enhancements (direct I/O, latency, mixed RandRW, optional trim/concurrency). Lean tests use shorter runtimes (60s) for efficiency. Total runtime ~1-1.25 hours.
- **Full Mode**: Adds comprehensive tests with full runtimes (300s for lean additions) and extra block sizes (512k). Total runtime ~2-3 hours.
- **Test Mode**: Runs partial core tests (4k randread, 64k randwrite, 1M read) with 15s runtime for quick validation. Total runtime ~1 minute.

Run the script with optional flags:

- `bash fio_benchmark.sh`: Lean mode (HDD, no concurrency).
- `bash fio_benchmark.sh --full`: Full mode with additional tests.
- `bash fio_benchmark.sh --test`: Test mode (15s runtime, partial core tests for quick validation).
- `bash fio_benchmark.sh --ssd`: Enable SSD-specific tests (e.g., trim).
- `bash fio_benchmark.sh --concurrency`: Enable high concurrency on select tests.
- `bash fio_benchmark.sh --full --ssd --concurrency`: Combine for comprehensive SSD testing.

**Note**: On macOS, ensure `fio` is installed (e.g., via Homebrew). Latency tracking (`--lat`) may not be supported in older fio versions and will be automatically disabled with a warning. Summary parsing is optimized for macOS fio output; use `--test` for quick checks.

Results are saved to bm_*.txt files.

## Summary Output

After running tests, the script automatically generates a summary of core metrics (IOPS, bandwidth, latency, CPU) in a table format. The summary is displayed on the console and saved to `summary.txt`. If the `column` tool is installed, the table is aligned; otherwise, a basic format is used.

Example output:
```
Test          IOPS Read  IOPS Write  BW Read    BW Write   Lat Avg Read (us)  Lat Avg Write (us)  CPU              Bar
randread 4k   15000      N/A         58.5MB/s   N/A        50.0               N/A                 usr=10.0% sys=5.0%  ####################
randwrite 4k  N/A        12000       N/A        46.7MB/s   N/A                70.0               usr=12.0% sys=6.0%  **********
...
```

The "Bar" column shows simple ASCII art for relative IOPS comparison (##### for read, **** for write), scaled to the maximum across all tests.
