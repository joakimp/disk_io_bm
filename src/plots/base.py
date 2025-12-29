"""Base plotter class"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
import webbrowser


class BasePlotter(ABC):
    """Abstract base class for plotters"""

    def __init__(self, results: List[dict], config: dict):
        self.results = results
        self.config = config
        self.output_dir = Path(config.get("plot_output_dir", "results/plots"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def generate(self) -> None:
        """Generate all plots"""
        pass

    @abstractmethod
    def save(self, filename: str) -> None:
        """Save plot to file"""
        pass

    def open_in_browser(self, filepath: str) -> bool:
        """Open HTML file in default browser

        Returns:
            bool: True if successful, False if failed
        """
        try:
            webbrowser.open(f"file://{Path(filepath).absolute()}")
            return True
        except Exception as e:
            print(f"Warning: Could not open browser: {e}")
            return False
