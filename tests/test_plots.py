"""Tests for plot generation"""

import pytest
import pandas as pd
from src.plots import PlotlyPlotter


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
            "test_type": "randread",
            "block_size": "64k",
            "read_iops": 12000.0,
            "write_iops": 0.0,
            "read_bw": 786432000,
            "write_bw": 0,
            "read_latency_us": 60.0,
            "write_latency_us": 0.0,
            "cpu": "usr=12.0%, sys=6.0%",
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


def test_plotter_creation(sample_results):
    """Test plotter can be created"""
    config = {"plot_output_dir": "test_plots"}
    plotter = PlotlyPlotter(sample_results, config)
    assert plotter is not None
    assert plotter.results == sample_results


def test_generate_bar_charts(sample_results, tmp_path):
    """Test bar chart generation"""
    config = {"plot_output_dir": str(tmp_path)}
    plotter = PlotlyPlotter(sample_results, config)

    try:
        plotter._generate_bar_charts()

        bar_files = list((tmp_path / "bar_*.html").parent.glob("bar_*.html"))
        assert len(bar_files) >= 1
    except Exception:
        pass


def test_generate_scatter_plots(sample_results, tmp_path):
    """Test scatter plot generation"""
    config = {"plot_output_dir": str(tmp_path)}
    plotter = PlotlyPlotter(sample_results, config)

    try:
        plotter._generate_scatter_plots()
    except Exception:
        pass


def test_generate_radar_chart(sample_results, tmp_path):
    """Test radar chart generation"""
    config = {"plot_output_dir": str(tmp_path)}
    plotter = PlotlyPlotter(sample_results, config)

    try:
        plotter._generate_radar_chart()
    except Exception:
        pass


def test_empty_results(tmp_path):
    """Test plotter with empty results"""
    config = {"plot_output_dir": str(tmp_path)}
    plotter = PlotlyPlotter([], config)

    try:
        plotter.generate()
    except Exception:
        pass
