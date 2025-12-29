"""FIO command execution module"""

import json
import subprocess
import tempfile
import platform
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

from src.config import BenchmarkConfig, Mode


class BenchmarkExecutor:
    """Execute FIO benchmark tests"""

    def __init__(self, config: BenchmarkConfig, console: Optional[Console] = None):
        self.config = config
        self.console = console or Console()
        self.temp_dir = Path(tempfile.mkdtemp(prefix="disk_benchmark_"))
        self.is_macos = platform.system() == "Darwin"

    def run_all_tests(self) -> List[dict]:
        """Run all benchmarks based on mode"""
        results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeRemainingColumn(),
            console=self.console,
        ) as progress:
            test_configs = self._get_test_configs()
            total_tests = len(test_configs)

            for idx, test_config in enumerate(test_configs):
                task = progress.add_task(
                    f"Running {test_config['test_type']} ({test_config['block_size']})",
                    total=total_tests,
                )

                result = self._run_single_test(test_config)
                if result:
                    results.append(result)

                progress.update(task, advance=1)

        return results

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
            if self.config.ssd:
                configs.append({"test_type": "trim", "block_size": "4k"})
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
            if self.config.ssd:
                configs.append({"test_type": "trim", "block_size": "4k"})
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

    def _run_single_test(self, test_config: dict) -> Optional[dict]:
        """Run a single FIO test"""
        test_file = self.temp_dir / f"test_{test_config['test_type']}_{test_config['block_size']}"

        try:
            cmd = self._build_fio_command(test_config, test_file)
            self.console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.runtime + 60,
            )

            if result.returncode == 0:
                parsed = self._parse_fio_json_output(result.stdout, test_config)
                parsed["status"] = "OK"
                parsed["output_file"] = str(test_file)
                return parsed
            else:
                self.console.print(f"[red]FIO test failed: {result.stderr}[/red]")
                return {
                    "test_type": test_config["test_type"],
                    "block_size": test_config["block_size"],
                    "status": f"FAILED: {result.stderr.strip()}",
                    "read_iops": 0,
                    "write_iops": 0,
                    "read_bw": 0,
                    "write_bw": 0,
                    "read_latency_us": 0,
                    "write_latency_us": 0,
                    "cpu": "N/A",
                    "runtime_sec": 0,
                }

        except subprocess.TimeoutExpired:
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
                "runtime_sec": 0,
            }
        except Exception as e:
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
                "runtime_sec": 0,
            }
        finally:
            if test_file.exists():
                test_file.unlink()

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

    def _parse_fio_json_output(self, output: str, test_config: dict) -> dict:
        """Parse FIO JSON output"""
        try:
            data = json.loads(output)
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
                "runtime_sec": job.get("runtime", 0) / 1000,
            }
        except json.JSONDecodeError:
            self.console.print("[red]Failed to parse FIO JSON output[/red]")
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

    def _empty_result(self, test_config: dict, reason: str = "Empty result") -> dict:
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
            "runtime_sec": 0,
        }
