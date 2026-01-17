"""
Base formatter class for output formatters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, TextIO
import sys

from bake_linter.core.models import LintResult, LintSummary


class BaseFormatter(ABC):
    """
    Abstract base class for output formatters.
    
    Formatters are responsible for presenting lint results to the user
    in various formats (text, JSON, HTML, etc.).
    """

    def __init__(
        self,
        output: Optional[TextIO] = None,
        color: bool = True,
        verbose: bool = False,
    ):
        """
        Initialize the formatter.
        
        Args:
            output: Output stream (defaults to stdout)
            color: Whether to use colored output
            verbose: Whether to include verbose details
        """
        self.output = output or sys.stdout
        self.color = color
        self.verbose = verbose

    @abstractmethod
    def format_results(self, results: List[LintResult], summary: LintSummary) -> str:
        """
        Format the lint results and summary.
        
        Args:
            results: List of lint results
            summary: Summary statistics
            
        Returns:
            Formatted string
        """
        pass

    def write(self, results: List[LintResult], summary: LintSummary) -> None:
        """
        Format and write results to output.
        
        Args:
            results: List of lint results
            summary: Summary statistics
        """
        formatted = self.format_results(results, summary)
        self.output.write(formatted)
        if not formatted.endswith("\n"):
            self.output.write("\n")

    def write_to_file(self, results: List[LintResult], summary: LintSummary, 
                      path: Path) -> None:
        """
        Format and write results to a file.
        
        Args:
            results: List of lint results
            summary: Summary statistics
            path: Output file path
        """
        formatted = self.format_results(results, summary)
        path.write_text(formatted, encoding="utf-8")
