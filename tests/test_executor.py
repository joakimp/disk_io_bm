"""Tests for benchmark executor with mocked FIO output"""

import json
import pytest
from src.config import BenchmarkConfig, Mode
from src.executor import BenchmarkExecutor


@pytest.fixture
def mock_fio_json_output():
    """Mock FIO JSON output for testing"""
    return json.dumps(
        {
            "jobs": [
                {
                    "read": {
                        "iops": 10000.5,
                        "bw_bytes": 41943040,
                        "lat_ns": {"mean": 50000.0},
                    },
                    "write": {},
                    "job_options": {
                        "cpu": {
                            "user": 5.5,
                            "system": 2.3,
                        },
                    },
                    "job_runtime": 15023,  # FIO reports job runtime in milliseconds
                }
            ]
        }
    )


def test_executor_creation():
    """Test executor can be created"""
    config = BenchmarkConfig()
    executor = BenchmarkExecutor(config)
    assert executor is not None
    assert executor.config is not None


def test_get_test_configs_lean_mode():
    """Test test configuration generation for lean mode"""
    config = BenchmarkConfig(mode=Mode.LEAN)
    executor = BenchmarkExecutor(config)
    configs = executor._get_test_configs()
    assert len(configs) == 13  # 4 block sizes * 3 tests + randrw
    test_types = {c["test_type"] for c in configs}
    assert "randread" in test_types
    assert "randwrite" in test_types
    assert "read" in test_types
    assert "write" in test_types
    assert "randrw" in test_types


def test_get_test_configs_test_mode():
    """Test test configuration generation for test mode"""
    config = BenchmarkConfig(mode=Mode.TEST)
    executor = BenchmarkExecutor(config)
    configs = executor._get_test_configs()
    assert len(configs) == 3
    assert configs[0] == {"test_type": "randread", "block_size": "4k"}
    assert configs[1] == {"test_type": "randwrite", "block_size": "64k"}
    assert configs[2] == {"test_type": "read", "block_size": "1M"}


def test_get_test_configs_individual_mode():
    """Test test configuration generation for individual mode"""
    config = BenchmarkConfig(
        mode=Mode.INDIVIDUAL,
        test_types=["randread", "write"],
        block_sizes=["4k", "1M"],
    )
    executor = BenchmarkExecutor(config)
    configs = executor._get_test_configs()
    # Should be 2 test types × 2 block sizes = 4 tests
    assert len(configs) == 4


def test_build_fio_command():
    """Test FIO command building"""
    config = BenchmarkConfig(
        mode=Mode.TEST,
        runtime=60,
        filesize="1G",
    )
    executor = BenchmarkExecutor(config)
    test_config = {"test_type": "read", "block_size": "4k"}
    cmd = executor._build_fio_command(test_config, executor.temp_dir / "test")
    assert "fio" in cmd
    assert "--name=benchmark" in cmd
    assert "--rw=read" in cmd
    assert "--bs=4k" in cmd
    assert "--runtime=60" in cmd
    assert "--size=1G" in cmd


def test_parse_fio_json_output(mock_fio_json_output):
    """Test FIO JSON output parsing"""
    config = BenchmarkConfig()
    executor = BenchmarkExecutor(config)
    test_config = {"test_type": "read", "block_size": "4k"}
    result = executor._parse_fio_json_output(mock_fio_json_output, test_config)
    assert result["test_type"] == "read"
    assert result["block_size"] == "4k"
    assert result["read_iops"] == 10000.5
    # Write metrics should be 0 for read test
    assert result["write_iops"] == 0
    assert result["read_bw"] == 41943040
    assert result["write_bw"] == 0
    assert abs(result["read_latency_us"] - 50.0) < 1
    assert result["write_latency_us"] == 0
    assert "usr=5.5%" in result["cpu"]
    assert result["io_time_sec"] == 15.023


def test_convert_latency():
    """Test latency conversion from nanoseconds to microseconds"""
    config = BenchmarkConfig()
    executor = BenchmarkExecutor(config)
    assert executor._convert_latency(50000) == 50.0
    assert executor._convert_latency(100000) == 100.0
    assert executor._convert_latency(0) == 0
