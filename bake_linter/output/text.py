"""
Text output formatter for human-readable CLI output.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Optional, TextIO
import sys

from bake_linter.core.models import LintResult, LintSummary, Severity
from bake_linter.output.base import BaseFormatter


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
            return "\n".join(lines)
        
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
    Format: file:line:column: severity: [rule_id] message
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
            lines.append(f"{loc}: {severity}: [{result.rule_id}] {result.message}")
        
        # Add summary line
        if results:
            lines.append("")
            lines.append(
                f"Found {summary.total_issues} issue(s): "
                f"{summary.errors} error(s), {summary.warnings} warning(s), {summary.infos} info(s)"
            )
        else:
            lines.append("No issues found.")
        
        return "\n".join(lines)
