"""Configuration management for disk I/O benchmarks"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List


class StorageBackend(Enum):
    """Storage backend options"""

    NONE = "none"
    SQLITE = "sqlite"
    CSV = "csv"
    JSON = "json"


class Mode(Enum):
    """Benchmark modes"""

    TEST = "test"
    LEAN = "lean"
    FULL = "full"
    INDIVIDUAL = "individual"


@dataclass
class BenchmarkConfig:
    """Benchmark configuration parameters"""

    # Disk parameters
    filesize: str = "10G"
    runtime: int = 300
    block_size: str = "4k"
    io_depth: int = 4
    num_jobs: int = 1
    direct_io: bool = True
    sync: bool = True

    # Mode
    mode: Mode = Mode.LEAN
    ssd: bool = False
    hdd: bool = False
    concurrency: bool = False
    quick: bool = False

    # Individual tests
    test_types: List[str] = field(default_factory=list)
    block_sizes: List[str] = field(default_factory=list)

    # Output
    results_dir: str = "results"
    output_format: str = "table"
    json_output_dir: str = "results/json"
    generate_plots: bool = False
    plot_types: List[str] = field(default_factory=list)
    plot_output_dir: str = "results/plots"
    interactive_plots: bool = False

    # Database
    database: StorageBackend = StorageBackend.SQLITE
    db_path: str = "results/benchmark_history.db"
    history: int = 10
    query_sql: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "BenchmarkConfig":
        """Create config from dictionary"""
        filtered_data = {
            k: v for k, v in data.items() if hasattr(cls, k) or k in cls.__dataclass_fields__
        }
        return cls(**filtered_data)
