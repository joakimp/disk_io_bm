"""Tests for table formatter"""

from io import StringIO
from rich.console import Console

from src.formatters import TableFormatter


def test_table_formatter_empty_results():
    """Test table formatter with no results"""
    console = Console(file=StringIO())
    formatter = TableFormatter(console)
    formatter.format([])
    output = console.file.getvalue()
    assert "No results to display" in output


def test_table_formatter_with_results():
    """Test table formatter with sample results"""
    console = Console(file=StringIO())
    formatter = TableFormatter(console)
    results = [
        {
            "test_type": "read",
            "block_size": "4k",
            "read_iops": 10000.5,
            "write_iops": 0,
            "read_bw": 41943040,
            "write_bw": 0,
            "read_latency_us": 50.0,
            "write_latency_us": 0,
            "cpu": "usr=5.5%, sys=2.3%",
            "runtime_sec": 15.0,
            "status": "OK",
        }
    ]
    formatter.format(results)
    output = console.file.getvalue()
    assert "read" in output.lower()
    assert "4k" in output
    assert "10000" in output or "100" in output
    assert "OK" in output


def test_table_formatter_with_failed_result():
    """Test table formatter with failed result"""
    console = Console(file=StringIO())
    formatter = TableFormatter(console)
    results = [
        {
            "test_type": "trim",
            "block_size": "4k",
            "read_iops": 0,
            "write_iops": 0,
            "read_bw": 0,
            "write_bw": 0,
            "read_latency_us": 0,
            "write_latency_us": 0,
            "cpu": "N/A",
            "runtime_sec": 0,
            "status": "FAILED: requires block device",
        }
    ]
    formatter.format(results)
    output = console.file.getvalue()
    assert "FAILED" in output or "FAI" in output
