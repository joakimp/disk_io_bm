"""FIO command execution module"""

import json
import subprocess
import tempfile
import platform
import time
import threading
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
    TaskProgressColumn,
)

from src.config import BenchmarkConfig, Mode


class BenchmarkExecutor:
    """Execute FIO benchmark tests"""

    def __init__(self, config: BenchmarkConfig, console: Optional[Console] = None):
        self.config = config
        self.console = console or Console()
        from pathlib import Path

        self.temp_dir = Path.cwd()
        self.is_macos = platform.system() == "Darwin"

    def run_all_tests(self) -> List[dict]:
        """Run all benchmarks based on mode"""
        results = []
        test_configs = self._get_test_configs()
        total_tests = len(test_configs)
        runtime = self.config.runtime

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("{task.fields[time_display]}"),
            console=self.console,
            refresh_per_second=2,
        ) as progress:
            for idx, test_config in enumerate(test_configs):
                description = f"[{idx + 1}/{total_tests}] {test_config['test_type']} ({test_config['block_size']})"
                task = progress.add_task(
                    description,
                    total=runtime,
                    time_display=f"[cyan]0s[/cyan] / [cyan]~{runtime}s[/cyan]",
                )

                result, wall_time = self._run_single_test_with_progress(
                    test_config, progress, task, runtime
                )
                if result:
                    results.append(result)

                # Update to show actual wall time when complete
                actual_time = int(wall_time)
                progress.update(
                    task,
                    completed=actual_time,
                    total=actual_time,
                    time_display=f"[cyan]{actual_time}s[/cyan] / [cyan]{actual_time}s[/cyan]",
                )

        return results

    def _run_single_test_with_progress(
        self, test_config: dict, progress: Progress, task, runtime: int
    ) -> tuple[Optional[dict], float]:
        """Run a single FIO test with progress updates.

        Returns:
            Tuple of (result dict or None, wall_time in seconds)
        """
        test_file = self.temp_dir / f"test_{test_config['test_type']}_{test_config['block_size']}"
        wall_start = time.time()
        stop_progress = threading.Event()

        def update_progress():
            """Background thread to update progress bar"""
            while not stop_progress.is_set():
                elapsed = time.time() - wall_start
                elapsed_int = int(elapsed)
                # Cap at runtime to avoid showing more than 100%
                progress.update(
                    task,
                    completed=min(elapsed, runtime),
                    time_display=f"[cyan]{elapsed_int}s[/cyan] / [cyan]~{runtime}s[/cyan]",
                )
                stop_progress.wait(0.5)

        # Start progress updater thread
        progress_thread = threading.Thread(target=update_progress, daemon=True)
        progress_thread.start()

        try:
            cmd = self._build_fio_command(test_config, test_file)
            self.console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.runtime + 60,
            )

            wall_time_sec = round(time.time() - wall_start, 2)

            if result.returncode == 0:
                parsed = self._parse_fio_json_output(result.stdout, test_config, allow_empty=True)
                parsed["status"] = "OK"
                parsed["output_file"] = str(test_file)
                parsed["wall_time_sec"] = wall_time_sec
                return parsed, wall_time_sec
            else:
                json_data = self._parse_fio_json_output(
                    result.stdout, test_config, allow_empty=True
                )
                is_valid_benchmark = (
                    json_data.get("read_iops", 0) > 0
                    or json_data.get("write_iops", 0) > 0
                    or json_data.get("read_bw", 0) > 0
                    or json_data.get("write_bw", 0) > 0
                    or json_data.get("io_time_sec", 0) > 0
                )

                if is_valid_benchmark:
                    json_data["status"] = "OK"
                    json_data["wall_time_sec"] = wall_time_sec
                    return json_data, wall_time_sec
                else:
                    stderr_msg = result.stderr.strip() if result.stderr else "unknown error"
                    self.console.print(f"[red]FIO test failed: {stderr_msg}[/red]")
                    return {
                        "test_type": test_config["test_type"],
                        "block_size": test_config["block_size"],
                        "status": f"FAILED: {stderr_msg}",
                        "read_iops": 0,
                        "write_iops": 0,
                        "read_bw": 0,
                        "write_bw": 0,
                        "read_latency_us": 0,
                        "write_latency_us": 0,
                        "cpu": "N/A",
                        "io_time_sec": 0,
                        "wall_time_sec": wall_time_sec,
                    }, wall_time_sec

        except subprocess.TimeoutExpired:
            wall_time_sec = round(time.time() - wall_start, 2)
            self.console.print(f"[red]Test timed out: {test_config['test_type']}[/red]")
            return {
                "test_type": test_config["test_type"],
                "block_size": test_config["block_size"],
                "status": "TIMED OUT",
                "read_iops": 0,
                "write_iops": 0,
                "read_bw": 0,
                "write_bw": 0,
                "read_latency_us": 0,
                "write_latency_us": 0,
                "cpu": "N/A",
                "io_time_sec": 0,
                "wall_time_sec": wall_time_sec,
            }, wall_time_sec
        except Exception as e:
            wall_time_sec = round(time.time() - wall_start, 2)
            self.console.print(f"[red]Error running test: {e}[/red]")
            return {
                "test_type": test_config["test_type"],
                "block_size": test_config["block_size"],
                "status": f"ERROR: {str(e)}",
                "read_iops": 0,
                "write_iops": 0,
                "read_bw": 0,
                "write_bw": 0,
                "read_latency_us": 0,
                "write_latency_us": 0,
                "cpu": "N/A",
                "io_time_sec": 0,
                "wall_time_sec": wall_time_sec,
            }, wall_time_sec
        finally:
            # Stop progress thread
            stop_progress.set()
            progress_thread.join(timeout=1)

            if test_file.exists():
                test_file.unlink()

    def _get_test_configs(self) -> List[dict]:
        """Get list of test configurations based on mode"""
        configs = []

        if self.config.mode == Mode.TEST:
            configs = [
                {"test_type": "randread", "block_size": "4k"},
                {"test_type": "randwrite", "block_size": "64k"},
                {"test_type": "read", "block_size": "1M"},
            ]
        elif self.config.mode == Mode.LEAN:
            configs = [
                {"test_type": "randread", "block_size": "4k"},
                {"test_type": "randwrite", "block_size": "4k"},
                {"test_type": "read", "block_size": "4k"},
                {"test_type": "write", "block_size": "4k"},
                {"test_type": "randread", "block_size": "64k"},
                {"test_type": "randwrite", "block_size": "64k"},
                {"test_type": "read", "block_size": "64k"},
                {"test_type": "write", "block_size": "64k"},
                {"test_type": "randread", "block_size": "1M"},
                {"test_type": "randwrite", "block_size": "1M"},
                {"test_type": "read", "block_size": "1M"},
                {"test_type": "write", "block_size": "1M"},
                {"test_type": "randrw", "block_size": "4k"},
            ]
        elif self.config.mode == Mode.FULL:
            block_sizes = ["4k", "64k", "1M", "512k"]
            for block_size in block_sizes:
                configs.extend(
                    [
                        {"test_type": "randread", "block_size": block_size},
                        {"test_type": "randwrite", "block_size": block_size},
                        {"test_type": "read", "block_size": block_size},
                        {"test_type": "write", "block_size": block_size},
                    ]
                )
            configs.append({"test_type": "randrw", "block_size": "4k"})
        elif self.config.mode == Mode.INDIVIDUAL:
            if not self.config.test_types or not self.config.block_sizes:
                self.console.print(
                    "[yellow]Individual mode requires --test-type and --block-size[/yellow]"
                )
                return []
            for test_type in self.config.test_types:
                for block_size in self.config.block_sizes:
                    if test_type == "trim" and block_size != "4k":
                        continue
                    configs.append({"test_type": test_type, "block_size": block_size})

        return configs

    def _build_fio_command(self, test_config: dict, test_file: Path) -> List[str]:
        """Build FIO command for a test"""
        cmd = [
            "fio",
            "--name=benchmark",
            f"--filename={test_file}",
            f"--size={self.config.filesize}",
            f"--rw={test_config['test_type']}",
            f"--bs={test_config['block_size']}",
            "--output-format=json",
            "--time_based",
        ]

        if self.is_macos:
            cmd.extend(
                [
                    "--ioengine=psync",
                    "--iodepth=1",
                    "--numjobs=1",
                ]
            )
        else:
            cmd.extend(
                [
                    f"--iodepth={self.config.io_depth}",
                    f"--numjobs={self.config.num_jobs}",
                ]
            )

        cmd.append(f"--runtime={self.config.runtime}")

        if self.config.direct_io and not self.is_macos:
            cmd.append("--direct=1")

        if self.config.sync:
            cmd.append("--fsync=1")
        else:
            cmd.append("--fsync=0")

        if test_config["test_type"] == "randrw":
            cmd.append("--rwmixread=70")

        if self.config.ssd and not self.is_macos:
            cmd.extend(
                [
                    "--iodepth_batch_submit_max=32",
                    "--iodepth_batch_complete_max=32",
                ]
            )

        if self.config.concurrency and not self.is_macos:
            cmd.extend(
                [
                    "--numjobs=4",
                    "--iodepth=16",
                ]
            )

        return cmd

    def _parse_fio_json_output(
        self, output: str, test_config: dict, allow_empty: bool = False
    ) -> dict:
        """Parse FIO JSON output"""
        try:
            # FIO may output non-JSON content (progress, warnings) before/after JSON
            # Extract just the JSON portion
            json_start = output.find("{")
            json_end = output.rfind("}") + 1
            if json_start == -1 or json_end == 0:
                self.console.print("[red]No JSON found in FIO output[/red]")
                if output.strip():
                    self.console.print(f"[dim]Raw output: {output[:500]}[/dim]")
                return self._empty_result(test_config, "No JSON in output")

            json_str = output[json_start:json_end]
            data = json.loads(json_str)
            jobs = data.get("jobs", [])

            if not jobs:
                return self._empty_result(test_config, "No jobs in output")

            job = jobs[0]
            read = job.get("read", {})
            write = job.get("write", {})

            # Handle cases where read/write metrics might be None
            read_iops = read.get("iops") if read else 0
            write_iops = write.get("iops") if write else 0

            return {
                "test_type": test_config["test_type"],
                "block_size": test_config["block_size"],
                "read_iops": read_iops if read_iops is not None else 0,
                "write_iops": write_iops if write_iops is not None else 0,
                "read_bw": read.get("bw_bytes", 0) if read else 0,
                "write_bw": write.get("bw_bytes", 0) if write else 0,
                "read_latency_us": self._convert_latency(
                    read.get("lat_ns", {}).get("mean", 0) if read else 0
                ),
                "write_latency_us": self._convert_latency(
                    write.get("lat_ns", {}).get("mean", 0) if write else 0
                ),
                "cpu": self._extract_cpu(job.get("job_options", {})),
                "io_time_sec": job.get("job_runtime", 0) / 1000,
            }
        except json.JSONDecodeError as e:
            self.console.print(f"[red]Failed to parse FIO JSON output: {e}[/red]")
            if output.strip():
                self.console.print(f"[dim]Raw output (first 500 chars): {output[:500]}[/dim]")
            return self._empty_result(test_config, "JSON parse error")

    def _convert_latency(self, latency_ns: float) -> float:
        """Convert latency from nanoseconds to microseconds"""
        return round(latency_ns / 1000, 2) if latency_ns else 0

    def _extract_cpu(self, job_options: dict) -> str:
        """Extract CPU usage from job options"""
        cpu = job_options.get("cpu", {})
        usr = cpu.get("user", 0)
        sys_val = cpu.get("system", 0)
        return f"usr={usr:.1f}%, sys={sys_val:.1f}%"

    def _empty_result(
        self, test_config: dict, reason: str = "Empty result", allow_empty: bool = False
    ) -> dict:
        """Return empty result placeholder"""
        return {
            "test_type": test_config["test_type"],
            "block_size": test_config["block_size"],
            "status": reason,
            "read_iops": 0,
            "write_iops": 0,
            "read_bw": 0,
            "write_bw": 0,
            "read_latency_us": 0,
            "write_latency_us": 0,
            "cpu": "N/A",
            "io_time_sec": 0,
            "wall_time_sec": 0,
        }
