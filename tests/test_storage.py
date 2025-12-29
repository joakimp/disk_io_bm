"""Tests for CSV storage and formatters"""

import pytest
import os
from pathlib import Path
from src.storage import CsvStorage
from src.formatters import CsvFormatter, ExcelFormatter
from src.config import BenchmarkConfig, Mode


@pytest.fixture
def sample_results():
    """Sample benchmark results for testing"""
    return [
        {
            "test_type": "randread",
            "block_size": "4k",
            "read_iops": 15000.0,
            "write_iops": 0.0,
            "read_bw": 61440000,
            "write_bw": 0,
            "read_latency_us": 50.0,
            "write_latency_us": 0.0,
            "cpu": "usr=10.0%, sys=5.0%",
            "runtime_sec": 15.0,
            "status": "OK",
        },
        {
            "test_type": "randwrite",
            "block_size": "4k",
            "read_iops": 0.0,
            "write_iops": 10000.0,
            "read_bw": 0,
            "write_bw": 40960000,
            "read_latency_us": 0.0,
            "write_latency_us": 70.0,
            "cpu": "usr=8.0%, sys=4.0%",
            "runtime_sec": 15.0,
            "status": "OK",
        },
    ]


@pytest.fixture
def sample_config():
    """Sample benchmark config"""
    return BenchmarkConfig(mode=Mode.LEAN, filesize="10G", runtime=300)


@pytest.fixture
def tmp_dir(tmp_path):
    """Temporary directory for tests"""
    return tmp_path


def test_csv_formatter_creation(tmp_dir):
    """Test CSV formatter creation"""
    formatter = CsvFormatter(str(tmp_dir / "test.csv"))
    assert formatter is not None


def test_csv_formatter_format(sample_results, tmp_dir):
    """Test CSV formatter output"""
    output_file = tmp_dir / "test_results.csv"
    formatter = CsvFormatter(str(output_file))
    formatter.format(sample_results)

    assert output_file.exists()

    with open(output_file, "r") as f:
        content = f.read()

    assert "Test Type" in content
    assert "randread" in content
    assert "randwrite" in content


def test_csv_formatter_empty(tmp_dir):
    """Test CSV formatter with empty results"""
    output_file = tmp_dir / "empty.csv"
    formatter = CsvFormatter(str(output_file))
    formatter.format([])

    assert not output_file.exists()


def test_csv_storage_creation(tmp_dir):
    """Test CSV storage creation"""
    storage = CsvStorage(str(tmp_dir))
    assert storage is not None
    assert storage.results_dir.exists()


def test_csv_storage_save(sample_results, sample_config, tmp_dir):
    """Test CSV storage save"""
    storage = CsvStorage(str(tmp_dir))
    storage.save_results(sample_results, sample_config)

    csv_files = list(tmp_dir.glob("benchmark_*.csv"))
    assert len(csv_files) > 0

    csv_file = csv_files[0]
    with open(csv_file, "r") as f:
        content = f.read()

    assert "# Disk I/O Benchmark Results" in content
    assert "randread" in content


def test_csv_storage_empty(sample_config, tmp_dir):
    """Test CSV storage with empty results"""
    storage = CsvStorage(str(tmp_dir))
    storage.save_results([], sample_config)

    csv_files = list(tmp_dir.glob("benchmark_*.csv"))
    assert len(csv_files) > 0


def test_excel_formatter_format(sample_results, tmp_dir):
    """Test Excel formatter output"""
    output_file = tmp_dir / "test_results.xlsx"
    formatter = ExcelFormatter(str(output_file))

    try:
        formatter.format(sample_results)
    except ImportError:
        pytest.skip("openpyxl or pandas not available")

    if output_file.exists():
        import pandas as pd

        xls = pd.ExcelFile(output_file)
        assert "Summary" in xls.sheet_names
        assert "Raw" in xls.sheet_names


def test_excel_formatter_empty(tmp_dir):
    """Test Excel formatter with empty results"""
    output_file = tmp_dir / "empty.xlsx"
    formatter = ExcelFormatter(str(output_file))

    try:
        formatter.format([])
        assert not output_file.exists()
    except ImportError:
        pytest.skip("openpyxl or pandas not available")
