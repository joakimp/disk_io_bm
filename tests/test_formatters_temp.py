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
