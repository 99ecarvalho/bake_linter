"""
JSON output formatter for machine-parseable output.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional, TextIO, Any, Dict

from bake_linter.core.models import LintResult, LintSummary
from bake_linter.output.base import BaseFormatter


class JsonFormatter(BaseFormatter):
    """
    JSON formatter for machine-parseable output.
    
    Produces structured JSON output suitable for CI integration,
    log aggregation, and programmatic consumption.
    
    Output schema:
    {
        "version": "1.0",
        "timestamp": "ISO8601",
        "summary": { ... },
        "results": [ ... ],
        "metadata": { ... }
    }
    """

    SCHEMA_VERSION = "1.0"

    def __init__(
        self,
        output: Optional[TextIO] = None,
        color: bool = False,  # Ignored for JSON
        verbose: bool = False,
        pretty: bool = True,
        include_metadata: bool = True,
    ):
        """
        Initialize the JSON formatter.
        
        Args:
            output: Output stream
            color: Ignored (no colors in JSON)
            verbose: Whether to include extra details
            pretty: Whether to pretty-print JSON
            include_metadata: Whether to include metadata block
        """
        super().__init__(output, color=False, verbose=verbose)
        self.pretty = pretty
        self.include_metadata = include_metadata

    def format_results(self, results: List[LintResult], summary: LintSummary) -> str:
        """Format results as JSON."""
        output: Dict[str, Any] = {
            "version": self.SCHEMA_VERSION,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "summary": self._format_summary(summary),
            "results": [self._format_result(r) for r in results],
        }
        
        if self.include_metadata:
            output["metadata"] = self._get_metadata()
        
        if self.pretty:
            return json.dumps(output, indent=2, ensure_ascii=False)
        return json.dumps(output, ensure_ascii=False)

    def _format_result(self, result: LintResult) -> Dict[str, Any]:
        """Format a single result as a dict."""
        return {
            "rule_id": result.rule_id,
            "rule_name": result.rule_name,
            "file": str(result.file),
            "line": result.line,
            "column": result.column,
            "severity": result.severity.name.lower(),
            "message": result.message,
            "hint": result.hint,
            "context": result.context if self.verbose else None,
        }

    def _format_summary(self, summary: LintSummary) -> Dict[str, Any]:
        """Format summary as a dict."""
        return {
            "files_scanned": summary.files_scanned,
            "files_with_issues": summary.files_with_issues,
            "total_issues": summary.total_issues,
            "errors": summary.errors,
            "warnings": summary.warnings,
            "infos": summary.infos,
            "rules_executed": summary.rules_executed,
            "skipped_files": summary.skipped_files if self.verbose else len(summary.skipped_files),
            "exit_code": summary.get_exit_code().value,
        }

    def _get_metadata(self) -> Dict[str, Any]:
        """Get metadata about the lint run."""
        import platform
        from bake_linter import __version__
        
        return {
            "linter_version": __version__,
            "python_version": platform.python_version(),
            "platform": platform.system(),
        }


class JsonLinesFormatter(BaseFormatter):
    """
    JSON Lines (NDJSON) formatter.
    
    Produces one JSON object per line, useful for streaming
    and log aggregation systems.
    """

    def __init__(
        self,
        output: Optional[TextIO] = None,
        color: bool = False,
        verbose: bool = False,
    ):
        super().__init__(output, color=False, verbose=verbose)

    def format_results(self, results: List[LintResult], summary: LintSummary) -> str:
        """Format results as JSON Lines (one JSON object per line)."""
        lines = []
        
        # Each result as a separate JSON line
        for result in results:
            obj = {
                "type": "result",
                "rule_id": result.rule_id,
                "rule_name": result.rule_name,
                "file": str(result.file),
                "line": result.line,
                "column": result.column,
                "severity": result.severity.name.lower(),
                "message": result.message,
                "hint": result.hint,
            }
            lines.append(json.dumps(obj))
        
        # Summary as final line
        summary_obj = {
            "type": "summary",
            "files_scanned": summary.files_scanned,
            "files_with_issues": summary.files_with_issues,
            "total_issues": summary.total_issues,
            "errors": summary.errors,
            "warnings": summary.warnings,
            "infos": summary.infos,
            "exit_code": summary.get_exit_code().value,
        }
        lines.append(json.dumps(summary_obj))
        
        return "\n".join(lines)
