"""Tests for configuration management"""

from src.config import BenchmarkConfig, Mode, StorageBackend


def test_default_config():
    """Test default configuration values"""
    config = BenchmarkConfig()
    assert config.mode == Mode.LEAN
    assert config.filesize == "10G"
    assert config.runtime == 300
    assert config.database == StorageBackend.SQLITE
    assert config.ssd is False
    assert config.concurrency is False


def test_config_from_dict():
    """Test creating config from dictionary"""
    data = {"mode": Mode.TEST, "runtime": 60, "filesize": "100M"}
    config = BenchmarkConfig.from_dict(data)
    assert config.mode == Mode.TEST
    assert config.runtime == 60
    assert config.filesize == "100M"


def test_mode_enum():
    """Test mode enum values"""
    assert Mode.TEST.value == "test"
    assert Mode.LEAN.value == "lean"
    assert Mode.FULL.value == "full"
    assert Mode.INDIVIDUAL.value == "individual"


def test_storage_backend_enum():
    """Test storage backend enum values"""
    assert StorageBackend.NONE.value == "none"
    assert StorageBackend.SQLITE.value == "sqlite"
    assert StorageBackend.JSON.value == "json"
