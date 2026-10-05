# -*- coding: utf-8 -*-
"""
Text output formatter for human-readable CLI output.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Optional, TextIO, TYPE_CHECKING
import sys

from bake_linter.core.models import LintResult, LintSummary, Severity
from bake_linter.output.base import BaseFormatter

if TYPE_CHECKING:
    from bake_linter.core.oelint_integration import OelintResult, OelintSummary


class Colors:
    """ANSI color codes for terminal output."""
    
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"


class TextFormatter(BaseFormatter):
    """
    Human-readable text formatter for CLI output.
    
    Provides colored, formatted output suitable for terminal display.
    Supports both colored and plain text modes for CI compatibility.
    """

    SEVERITY_COLORS = {
        Severity.ERROR: Colors.RED,
        Severity.WARNING: Colors.YELLOW,
        Severity.INFO: Colors.BLUE,
    }

    SEVERITY_SYMBOLS = {
        Severity.ERROR: "✖",
        Severity.WARNING: "⚠",
        Severity.INFO: "ℹ",
    }

    SEVERITY_SYMBOLS_ASCII = {
        Severity.ERROR: "[E]",
        Severity.WARNING: "[W]",
        Severity.INFO: "[I]",
    }

    def __init__(
        self,
        output: Optional[TextIO] = None,
        color: bool = True,
        verbose: bool = False,
        use_unicode: bool = True,
    ):
        """
        Initialize the text formatter.
        
        Args:
            output: Output stream
            color: Whether to use ANSI colors
            verbose: Whether to show detailed output
            use_unicode: Whether to use Unicode symbols
        """
        super().__init__(output, color, verbose)
        self.use_unicode = use_unicode
        self.symbols = self.SEVERITY_SYMBOLS if use_unicode else self.SEVERITY_SYMBOLS_ASCII

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if self.color:
            return f"{color}{text}{Colors.RESET}"
        return text

    def _format_severity(self, severity: Severity) -> str:
        """Format severity with color and symbol."""
        symbol = self.symbols[severity]
        color = self.SEVERITY_COLORS[severity]
        return self._colorize(f"{symbol} {severity.name}", color)

    def _format_location(self, result: LintResult) -> str:
        """Format file location."""
        loc = str(result.file)
        if result.line:
            loc += f":{result.line}"
            if result.column:
                loc += f":{result.column}"
        return self._colorize(loc, Colors.CYAN)

    def format_results(self, results: List[LintResult], summary: LintSummary) -> str:
        """Format results as human-readable text."""
        lines = []
        
        if not results:
            lines.append(self._colorize("✓ No issues found!", Colors.GREEN))
            lines.append("")
            lines.append(self._format_summary(summary))
        else:
            # Group results by file
            by_file: Dict[Path, List[LintResult]] = {}
            for result in results:
                if result.file not in by_file:
                    by_file[result.file] = []
                by_file[result.file].append(result)
            
            # Format each file's results
            for file_path in sorted(by_file.keys()):
                file_results = by_file[file_path]
                
                # File header
                lines.append("")
                lines.append(self._colorize(f"━━━ {file_path} ━━━", Colors.BOLD))
                
                # Results for this file
                for result in sorted(file_results, key=lambda r: r.line or 0):
                    lines.append(self._format_result(result))
            
            # Summary
            lines.append("")
            lines.append(self._format_summary(summary))
        
        # Append oelint-adv results if available
        if self.oelint_results is not None and self.oelint_summary is not None:
            lines.append("")
            lines.append(self._format_oelint_section())
        
        return "\n".join(lines)

    def _format_oelint_section(self) -> str:
        """Format oelint-adv results section."""
        lines = []
        
        # Section header
        lines.append(self._colorize("═" * 60, Colors.MAGENTA))
        lines.append(self._colorize("  oelint-adv Analysis Results", Colors.MAGENTA + Colors.BOLD))
        if self.oelint_summary and self.oelint_summary.tool_version:
            lines.append(self._colorize(f"  Version: {self.oelint_summary.tool_version}", Colors.DIM))
        lines.append(self._colorize("═" * 60, Colors.MAGENTA))
        
        if not self.oelint_results:
            lines.append(self._colorize("  ✓ No issues found by oelint-adv!", Colors.GREEN))
        else:
            # Group results by file
            by_file: Dict[Path, List["OelintResult"]] = {}
            for result in self.oelint_results:
                if result.file not in by_file:
                    by_file[result.file] = []
                by_file[result.file].append(result)
            
            # Format each file's results
            for file_path in sorted(by_file.keys()):
                file_results = by_file[file_path]
                
                # File header
                lines.append("")
                lines.append(self._colorize(f"━━━ {file_path} ━━━", Colors.BOLD))
                
                # Results for this file
                for result in sorted(file_results, key=lambda r: r.line):
                    lines.append(self._format_oelint_result(result))
        
        # Summary
        lines.append("")
        lines.append(self._format_oelint_summary())
        
        return "\n".join(lines)

    def _format_oelint_result(self, result: "OelintResult") -> str:
        """Format a single oelint-adv result."""
        parts = []
        
        # Location
        loc = f"  Line {result.line}"
        parts.append(self._colorize(loc, Colors.DIM))
        
        # Severity with color
        severity_colors = {
            'error': Colors.RED,
            'warning': Colors.YELLOW,
            'info': Colors.BLUE,
        }
        severity_symbols = {
            'error': "✖" if self.use_unicode else "[E]",
            'warning': "⚠" if self.use_unicode else "[W]",
            'info': "ℹ" if self.use_unicode else "[I]",
        }
        color = severity_colors.get(result.severity, Colors.WHITE)
        symbol = severity_symbols.get(result.severity, "?")
        severity_str = self._colorize(f"{symbol} {result.severity.upper()}", color)
        
        # Rule ID
        rule_str = self._colorize(f"[{result.rule_id}]", Colors.DIM)
        parts.append(f"  {severity_str} {rule_str}")
        
        # Message
        parts.append(f"    {result.message}")
        
        # Extra info if available
        if self.verbose and result.extra:
            parts.append(self._colorize(f"    │ {result.extra}", Colors.DIM))
        
        return "\n".join(parts)

    def _format_oelint_summary(self) -> str:
        """Format the oelint-adv summary section."""
        lines = []
        
        if not self.oelint_summary:
            return ""
        
        summary = self.oelint_summary
        
        # Divider
        lines.append(self._colorize("─" * 60, Colors.DIM))
        
        # Counts
        parts = []
        
        if summary.errors > 0:
            parts.append(self._colorize(f"{summary.errors} error(s)", Colors.RED))
        if summary.warnings > 0:
            parts.append(self._colorize(f"{summary.warnings} warning(s)", Colors.YELLOW))
        if summary.infos > 0:
            parts.append(self._colorize(f"{summary.infos} info(s)", Colors.BLUE))
        
        if parts:
            lines.append("  oelint-adv: " + ", ".join(parts))
        else:
            lines.append("  oelint-adv: No issues")
        
        # Stats
        stats = f"  {summary.files_scanned} file(s) scanned"
        if summary.files_with_issues > 0:
            stats += f", {summary.files_with_issues} with issues"
        stats += f", {len(summary.rules_triggered)} rule(s) triggered"
        lines.append(self._colorize(stats, Colors.DIM))
        
        return "\n".join(lines)

    def _format_result(self, result: LintResult) -> str:
        """Format a single lint result."""
        parts = []
        
        # Location
        if result.line:
            loc = f"  Line {result.line}"
            if result.column:
                loc += f":{result.column}"
            parts.append(self._colorize(loc, Colors.DIM))
        
        # Severity and rule
        severity_str = self._format_severity(result.severity)
        rule_str = self._colorize(f"[{result.rule_id}]", Colors.DIM)
        parts.append(f"  {severity_str} {rule_str}")
        
        # Message
        parts.append(f"    {result.message}")
        
        # Context (if verbose)
        if self.verbose and result.context:
            parts.append(self._colorize(f"    │ {result.context}", Colors.DIM))
        
        # Hint
        if result.hint:
            hint_text = f"    💡 {result.hint}" if self.use_unicode else f"    -> {result.hint}"
            parts.append(self._colorize(hint_text, Colors.GREEN))
        
        # Documentation reference
        if result.docs_url:
            docs_text = f"    📚 {result.docs_url}" if self.use_unicode else f"    [docs] {result.docs_url}"
            parts.append(self._colorize(docs_text, Colors.CYAN))
        
        return "\n".join(parts)

    def _format_summary(self, summary: LintSummary) -> str:
        """Format the summary section."""
        lines = []
        
        # Divider
        lines.append(self._colorize("─" * 60, Colors.DIM))
        
        # Counts
        parts = []
        
        if summary.errors > 0:
            parts.append(self._colorize(f"{summary.errors} error(s)", Colors.RED))
        if summary.warnings > 0:
            parts.append(self._colorize(f"{summary.warnings} warning(s)", Colors.YELLOW))
        if summary.infos > 0:
            parts.append(self._colorize(f"{summary.infos} info(s)", Colors.BLUE))
        
        if parts:
            lines.append("  " + ", ".join(parts))
        
        # Stats
        stats = f"  {summary.files_scanned} file(s) scanned"
        if summary.files_with_issues > 0:
            stats += f", {summary.files_with_issues} with issues"
        stats += f", {summary.rules_executed} rule(s) executed"
        lines.append(self._colorize(stats, Colors.DIM))
        
        # Skipped files
        if summary.skipped_files:
            lines.append(self._colorize(f"  {len(summary.skipped_files)} file(s) skipped", Colors.DIM))
            if self.verbose:
                for skipped in summary.skipped_files[:5]:
                    lines.append(self._colorize(f"    - {skipped}", Colors.DIM))
                if len(summary.skipped_files) > 5:
                    lines.append(self._colorize(f"    ... and {len(summary.skipped_files) - 5} more", Colors.DIM))
        
        return "\n".join(lines)


class CompactTextFormatter(TextFormatter):
    """
    Compact text formatter for CI output.
    
    Produces one-line-per-issue output suitable for CI parsing.
    Format: file:line:column: severity: [rule_id] message: doc: docs_url
    """

    def format_results(self, results: List[LintResult], summary: LintSummary) -> str:
        """Format results in compact one-line-per-issue format."""
        lines = []
        
        for result in sorted(results):
            loc = str(result.file)
            if result.line:
                loc += f":{result.line}"
                if result.column:
                    loc += f":{result.column}"
            
            severity = result.severity.name.lower()
            docs_ref = f": {result.docs_url}" if result.docs_url else ""
            lines.append(f"{loc}: {severity}: [{result.rule_id}] {result.message}{docs_ref}")
        
        # Add summary line
        if results:
            lines.append("")
            lines.append(
                f"Found {summary.total_issues} issue(s): "
                f"{summary.errors} error(s), {summary.warnings} warning(s), {summary.infos} info(s)"
            )
        else:
            lines.append("No issues found.")
        
        # Append oelint-adv results if available
        if self.oelint_results is not None and self.oelint_summary is not None:
            lines.append("")
            lines.append("=== oelint-adv ===")
            
            for result in sorted(self.oelint_results, key=lambda r: (str(r.file), r.line)):
                loc = f"{result.file}:{result.line}"
                lines.append(f"{loc}: {result.severity}: [{result.rule_id}] {result.message}")
            
            if self.oelint_results:
                lines.append("")
                lines.append(
                    f"oelint-adv found {self.oelint_summary.total_issues} issue(s): "
                    f"{self.oelint_summary.errors} error(s), {self.oelint_summary.warnings} warning(s), "
                    f"{self.oelint_summary.infos} info(s)"
                )
            else:
                lines.append("oelint-adv: No issues found.")
        
        return "\n".join(lines)
