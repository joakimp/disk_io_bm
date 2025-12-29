"""Tests for analytics functionality"""

import pytest
from src.analytics import Statistics, Comparison


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
            "runtime_sec": 15.0,
        },
        {
            "test_type": "randread",
            "block_size": "4k",
            "read_iops": 15500.0,
            "write_iops": 0.0,
            "read_bw": 63488000,
            "write_bw": 0,
            "read_latency_us": 48.0,
            "write_latency_us": 0.0,
            "runtime_sec": 15.0,
        },
        {
            "test_type": "randread",
            "block_size": "64k",
            "read_iops": 12000.0,
            "write_iops": 0.0,
            "read_bw": 786432000,
            "write_bw": 0,
            "read_latency_us": 60.0,
            "write_latency_us": 0.0,
            "runtime_sec": 15.0,
        },
    ]


def test_statistics_basic(sample_results):
    """Test basic statistics calculation"""
    stats = Statistics.calculate_basic(sample_results)

    assert stats is not None
    assert len(stats) > 0

    randread_4k = stats.get("randread_4k", {})
    assert "read_iops" in randread_4k
    assert "mean" in randread_4k["read_iops"]
    assert "median" in randread_4k["read_iops"]
    assert "min" in randread_4k["read_iops"]
    assert "max" in randread_4k["read_iops"]

    expected_mean = (15000.0 + 15500.0) / 2
    assert abs(randread_4k["read_iops"]["mean"] - expected_mean) < 0.01


def test_statistics_detailed(sample_results):
    """Test detailed statistics calculation"""
    stats = Statistics.calculate_detailed(sample_results)

    assert stats is not None
    assert len(stats) > 0

    randread_4k = stats.get("randread_4k", {})
    assert "read_iops" in randread_4k
    assert "std" in randread_4k["read_iops"]
    assert "q25" in randread_4k["read_iops"]
    assert "q75" in randread_4k["read_iops"]
    assert "count" in randread_4k["read_iops"]

    assert randread_4k["read_iops"]["count"] == 2


def test_statistics_format_basic(sample_results):
    """Test basic statistics formatting"""
    stats = Statistics.calculate_basic(sample_results)
    formatted = Statistics.format_basic(stats)

    assert formatted is not None
    assert "Statistics Summary" in formatted
    assert "randread_4k" in formatted


def test_statistics_format_detailed(sample_results):
    """Test detailed statistics formatting"""
    stats = Statistics.calculate_detailed(sample_results)
    formatted = Statistics.format_detailed(stats)

    assert formatted is not None
    assert "Detailed Statistics" in formatted
    assert "randread_4k" in formatted


def test_statistics_empty():
    """Test statistics with empty results"""
    stats = Statistics.calculate_basic([])
    assert stats == {}

    stats = Statistics.calculate_detailed([])
    assert stats == {}


def test_compare_runs():
    """Test run comparison"""
    run1 = [
        {
            "test_type": "randread",
            "block_size": "4k",
            "read_iops": 15000.0,
            "write_iops": 0.0,
            "read_bw": 61440000,
            "write_bw": 0,
            "read_latency_us": 50.0,
            "write_latency_us": 0.0,
            "runtime_sec": 15.0,
        }
    ]

    run2 = [
        {
            "test_type": "randread",
            "block_size": "4k",
            "read_iops": 16500.0,
            "write_iops": 0.0,
            "read_bw": 67584000,
            "write_bw": 0,
            "read_latency_us": 45.0,
            "write_latency_us": 0.0,
            "runtime_sec": 15.0,
        }
    ]

    comparison = Comparison.compare_runs(run1, run2, threshold=0.1)

    assert "run1" in comparison
    assert "run2" in comparison
    assert "deltas" in comparison
    assert "significant_changes" in comparison

    assert len(comparison["deltas"]) > 0

    first_delta = comparison["deltas"][0]
    assert "read_iops_abs" in first_delta
    assert "read_iops_pct" in first_delta


def test_compare_runs_empty():
    """Test comparison with empty runs"""
    comparison = Comparison.compare_runs([], [], threshold=0.1)
    assert "error" in comparison

    comparison = Comparison.compare_runs(
        [
            {
                "test_type": "randread",
                "block_size": "4k",
                "read_iops": 15000.0,
                "write_iops": 0.0,
            }
        ],
        [],
        threshold=0.1,
    )
    assert "error" in comparison


def test_comparison_formatting():
    """Test comparison formatting"""
    run1 = [
        {
            "test_type": "randread",
            "block_size": "4k",
            "read_iops": 15000.0,
            "write_iops": 0.0,
        }
    ]

    run2 = [
        {
            "test_type": "randread",
            "block_size": "4k",
            "read_iops": 18000.0,
            "write_iops": 0.0,
        }
    ]

    comparison = Comparison.compare_runs(run1, run2, threshold=0.1)
    formatted = Comparison.format_comparison(comparison)

    assert formatted is not None
    assert "Run Comparison" in formatted
    assert "randread" in formatted


def test_comparison_threshold():
    """Test threshold filtering in comparison"""
    run1 = [
        {
            "test_type": "randread",
            "block_size": "4k",
            "read_iops": 15000.0,
            "write_iops": 0.0,
        }
    ]

    run2 = [
        {
            "test_type": "randread",
            "block_size": "4k",
            "read_iops": 15500.0,
            "write_iops": 0.0,
        }
    ]

    comparison_low = Comparison.compare_runs(run1, run2, threshold=0.1)
    comparison_high = Comparison.compare_runs(run1, run2, threshold=0.01)

    assert len(comparison_low["significant_changes"]) < len(comparison_high["significant_changes"])
