"""Tests for storage backends (SQLite, CSV, JSON)"""

import pytest
from src.storage import CsvStorage, SQLiteStorage, JsonStorage
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


# SQLite Storage Tests


def test_sqlite_storage_creation(tmp_dir):
    """Test SQLite storage creation and database initialization"""
    db_path = tmp_dir / "test_benchmark.db"
    storage = SQLiteStorage(str(db_path))
    assert storage is not None
    assert db_path.exists()


def test_sqlite_storage_save_and_retrieve(sample_results, sample_config, tmp_dir):
    """Test SQLite storage save and retrieval"""
    db_path = tmp_dir / "test_benchmark.db"
    storage = SQLiteStorage(str(db_path))

    # Save results
    storage.save_results(sample_results, sample_config)

    # Retrieve results
    history = storage.get_history(10)
    assert len(history) == 2

    # Check that data was saved correctly
    assert any(r["test_type"] == "randread" for r in history)
    assert any(r["test_type"] == "randwrite" for r in history)

    # Check specific values
    randread_result = next(r for r in history if r["test_type"] == "randread")
    assert randread_result["block_size"] == "4k"
    assert randread_result["read_iops"] == 15000.0
    assert randread_result["status"] == "OK"


def test_sqlite_storage_multiple_saves(sample_results, sample_config, tmp_dir):
    """Test SQLite storage with multiple save operations"""
    db_path = tmp_dir / "test_benchmark.db"
    storage = SQLiteStorage(str(db_path))

    # Save results twice
    storage.save_results(sample_results, sample_config)
    storage.save_results(sample_results, sample_config)

    # Should have 4 records (2 results × 2 saves)
    history = storage.get_history(10)
    assert len(history) == 4


def test_sqlite_storage_custom_query(sample_results, sample_config, tmp_dir):
    """Test SQLite storage custom query"""
    db_path = tmp_dir / "test_benchmark.db"
    storage = SQLiteStorage(str(db_path))
    storage.save_results(sample_results, sample_config)

    # Query for specific test type
    results = storage.custom_query("SELECT * FROM benchmarks WHERE test_type = ?", ("randread",))
    assert len(results) == 1
    assert results[0]["test_type"] == "randread"


def test_sqlite_storage_empty_results(sample_config, tmp_dir):
    """Test SQLite storage with empty results"""
    db_path = tmp_dir / "test_benchmark.db"
    storage = SQLiteStorage(str(db_path))
    storage.save_results([], sample_config)

    history = storage.get_history(10)
    assert len(history) == 0


# JSON Storage Tests


def test_json_storage_creation(tmp_dir):
    """Test JSON storage creation"""
    storage = JsonStorage(str(tmp_dir))
    assert storage is not None
    assert tmp_dir.exists()


def test_json_storage_save(sample_results, sample_config, tmp_dir):
    """Test JSON storage save"""
    storage = JsonStorage(str(tmp_dir))
    storage.save_results(sample_results, sample_config)

    # Check that JSON file was created
    json_file = tmp_dir / "benchmark_results.json"
    assert json_file.exists()

    # Verify content
    import json

    with open(json_file, "r") as f:
        data = json.load(f)

    assert "timestamp" in data
    assert "results" in data
    assert len(data["results"]) == 2
