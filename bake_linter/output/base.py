# -*- coding: utf-8 -*-
"""
Base formatter class for output formatters.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, TextIO, TYPE_CHECKING
import sys

from bake_linter.core.models import LintResult, LintSummary

if TYPE_CHECKING:
    from bake_linter.core.oelint_integration import OelintResult, OelintSummary


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
        
        # oelint-adv data (set externally before write)
        self.oelint_results: Optional[List["OelintResult"]] = None
        self.oelint_summary: Optional["OelintSummary"] = None

    def set_oelint_data(
        self,
        results: Optional[List["OelintResult"]],
        summary: Optional["OelintSummary"],
    ) -> None:
        """
        Set oelint-adv data to be included in output.
        
        Args:
            results: List of oelint-adv results
            summary: Oelint-adv summary
        """
        self.oelint_results = results
        self.oelint_summary = summary

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
