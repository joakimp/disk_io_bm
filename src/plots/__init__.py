"""Plot generation for benchmark results"""

from .plotly import PlotlyPlotter

__all__ = ["PlotlyPlotter"]


def create_plotter(plot_type: str, results: list, config: dict):
    """Factory function to create appropriate plotter"""
    plotter = PlotlyPlotter(results, config)
    return plotter
