# -*- coding: utf-8 -*-
"""
JSON output formatter for machine-parseable output.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional, TextIO, Any, Dict, TYPE_CHECKING

from bake_linter.core.models import LintResult, LintSummary
from bake_linter.output.base import BaseFormatter

if TYPE_CHECKING:
    from bake_linter.core.oelint_integration import OelintResult, OelintSummary


class JsonFormatter(BaseFormatter):
    """
    JSON formatter for machine-parseable output.
    
    Produces structured JSON output suitable for CI integration,
    log aggregation, and programmatic consumption.
    
    Output schema:
    {
        "version": "1.1",
        "timestamp": "ISO8601",
        "bake_linter": {
            "summary": { ... },
            "results": [ ... ],
        },
        "oelint_adv": {  // optional, only if oelint-adv data available
            "summary": { ... },
            "results": [ ... ],
        },
        "metadata": { ... }
    }
    """

    SCHEMA_VERSION = "1.1"

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
            "bake_linter": {
                "summary": self._format_summary(summary),
                "results": [self._format_result(r) for r in results],
            },
        }
        
        # Add oelint-adv data if available
        if self.oelint_results is not None and self.oelint_summary is not None:
            output["oelint_adv"] = {
                "summary": self._format_oelint_summary(self.oelint_summary),
                "results": [self._format_oelint_result(r) for r in self.oelint_results],
            }
        
        if self.include_metadata:
            output["metadata"] = self._get_metadata()
        
        if self.pretty:
            return json.dumps(output, indent=2, ensure_ascii=False)
        return json.dumps(output, ensure_ascii=False)

    def _format_result(self, result: LintResult) -> Dict[str, Any]:
        """Format a single bake_linter result as a dict."""
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
            "docs_url": result.docs_url,
        }

    def _format_oelint_result(self, result: "OelintResult") -> Dict[str, Any]:
        """Format a single oelint-adv result as a dict."""
        return {
            "rule_id": result.rule_id,
            "rule_group": result.rule_group,
            "rule_subgroup": result.rule_subgroup,
            "file": str(result.file),
            "line": result.line,
            "severity": result.severity,
            "message": result.message,
            "extra": result.extra,
        }

    def _format_summary(self, summary: LintSummary) -> Dict[str, Any]:
        """Format bake_linter summary as a dict."""
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

    def _format_oelint_summary(self, summary: "OelintSummary") -> Dict[str, Any]:
        """Format oelint-adv summary as a dict."""
        return {
            "files_scanned": summary.files_scanned,
            "files_with_issues": summary.files_with_issues,
            "total_issues": summary.total_issues,
            "errors": summary.errors,
            "warnings": summary.warnings,
            "infos": summary.infos,
            "rules_triggered": sorted(summary.rules_triggered),
            "tool_version": summary.tool_version,
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
        
        # Each bake_linter result as a separate JSON line
        for result in results:
            obj = {
                "type": "bake_linter_result",
                "source": "bake_linter",
                "rule_id": result.rule_id,
                "rule_name": result.rule_name,
                "file": str(result.file),
                "line": result.line,
                "column": result.column,
                "severity": result.severity.name.lower(),
                "message": result.message,
                "hint": result.hint,
                "docs_url": result.docs_url,
            }
            lines.append(json.dumps(obj))
        
        # bake_linter summary
        summary_obj = {
            "type": "bake_linter_summary",
            "source": "bake_linter",
            "files_scanned": summary.files_scanned,
            "files_with_issues": summary.files_with_issues,
            "total_issues": summary.total_issues,
            "errors": summary.errors,
            "warnings": summary.warnings,
            "infos": summary.infos,
            "exit_code": summary.get_exit_code().value,
        }
        lines.append(json.dumps(summary_obj))
        
        # Add oelint-adv results if available
        if self.oelint_results is not None and self.oelint_summary is not None:
            # Each oelint-adv result as a separate JSON line
            for result in self.oelint_results:
                obj = {
                    "type": "oelint_adv_result",
                    "source": "oelint_adv",
                    "rule_id": result.rule_id,
                    "rule_group": result.rule_group,
                    "rule_subgroup": result.rule_subgroup,
                    "file": str(result.file),
                    "line": result.line,
                    "severity": result.severity,
                    "message": result.message,
                    "extra": result.extra,
                }
                lines.append(json.dumps(obj))
            
            # oelint-adv summary
            oelint_summary_obj = {
                "type": "oelint_adv_summary",
                "source": "oelint_adv",
                "files_scanned": self.oelint_summary.files_scanned,
                "files_with_issues": self.oelint_summary.files_with_issues,
                "total_issues": self.oelint_summary.total_issues,
                "errors": self.oelint_summary.errors,
                "warnings": self.oelint_summary.warnings,
                "infos": self.oelint_summary.infos,
                "rules_triggered": sorted(self.oelint_summary.rules_triggered),
                "tool_version": self.oelint_summary.tool_version,
            }
            lines.append(json.dumps(oelint_summary_obj))
        
        return "\n".join(lines)
