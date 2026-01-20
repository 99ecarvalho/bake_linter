# -*- coding: utf-8 -*-
"""
Integration module for oelint-adv tool.

This module provides functionality to detect, execute, and parse output from
the oelint-adv tool when it's available in the vendor directory.

oelint-adv is an advanced OELint tool that checks bitbake recipes against 
OECore styleguide.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bake_linter.core.models import Severity


@dataclass
class OelintResult:
    """
    Represents a single lint issue found by oelint-adv.
    
    Attributes:
        file: Path to the file where the issue was found
        line: Line number (1-indexed)
        severity: Severity level (error, warning, info)
        rule_id: Full rule identifier (e.g., oelint.var.mandatoryvar.HOMEPAGE)
        message: Human-readable description of the issue
        extra: Optional extra metadata (e.g., branch info)
    """
    file: Path
    line: int
    severity: str  # 'error', 'warning', 'info'
    rule_id: str
    message: str
    extra: Optional[str] = None

    @property
    def rule_group(self) -> str:
        """Extract the rule group from rule_id (e.g., 'var' from 'oelint.var.mandatoryvar')."""
        parts = self.rule_id.split('.')
        if len(parts) >= 2:
            return parts[1]
        return 'other'

    @property
    def rule_subgroup(self) -> str:
        """Extract the rule subgroup (e.g., 'mandatoryvar' from 'oelint.var.mandatoryvar')."""
        parts = self.rule_id.split('.')
        if len(parts) >= 3:
            return parts[2]
        return self.rule_group

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "file": str(self.file),
            "line": self.line,
            "severity": self.severity,
            "rule_id": self.rule_id,
            "rule_group": self.rule_group,
            "rule_subgroup": self.rule_subgroup,
            "message": self.message,
            "extra": self.extra,
        }


@dataclass
class OelintSummary:
    """
    Summary statistics for an oelint-adv run.
    
    Attributes:
        files_scanned: Number of files processed
        files_with_issues: Number of files that had at least one issue
        total_issues: Total number of issues found
        errors: Number of error-level issues
        warnings: Number of warning-level issues
        infos: Number of info-level issues
        rules_triggered: Set of rules that generated at least one issue
        tool_version: Version of oelint-adv if available
    """
    files_scanned: int = 0
    files_with_issues: int = 0
    total_issues: int = 0
    errors: int = 0
    warnings: int = 0
    infos: int = 0
    rules_triggered: List[str] = field(default_factory=list)
    tool_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "files_scanned": self.files_scanned,
            "files_with_issues": self.files_with_issues,
            "total_issues": self.total_issues,
            "errors": self.errors,
            "warnings": self.warnings,
            "infos": self.infos,
            "rules_triggered": sorted(self.rules_triggered),
            "tool_version": self.tool_version,
        }

    @classmethod
    def from_results(cls, results: List[OelintResult], 
                     files_scanned: int = 0,
                     tool_version: Optional[str] = None) -> "OelintSummary":
        """Create summary from a list of oelint results."""
        files_with_issues = len({str(r.file) for r in results})
        errors = sum(1 for r in results if r.severity == 'error')
        warnings = sum(1 for r in results if r.severity == 'warning')
        infos = sum(1 for r in results if r.severity == 'info')
        rules_triggered = list({r.rule_id for r in results})
        
        return cls(
            files_scanned=files_scanned,
            files_with_issues=files_with_issues,
            total_issues=len(results),
            errors=errors,
            warnings=warnings,
            infos=infos,
            rules_triggered=rules_triggered,
            tool_version=tool_version,
        )


class OelintAdvIntegration:
    """
    Integration handler for oelint-adv tool.
    
    Detects, configures, executes, and parses output from oelint-adv
    when available in the vendor directory.
    """

    # Regex to parse oelint-adv output lines
    # Format: /path/to/file.bb:line:severity:rule_id:message [extra]
    OUTPUT_PATTERN = re.compile(
        r'^(?P<file>.+?):(?P<line>\d+):(?P<severity>error|warning|info):(?P<rule_id>[\w.]+):(?P<message>.+?)(?:\s*\[(?P<extra>[^\]]+)\])?$'
    )

    def __init__(self, vendor_path: Optional[Path] = None):
        """
        Initialize the oelint-adv integration.
        
        Args:
            vendor_path: Path to the vendor directory containing oelint-adv.
                        If None, will try to detect from the bake_linter location.
        """
        self._vendor_path = vendor_path
        self._oelint_path: Optional[Path] = None
        self._venv_python: Optional[Path] = None
        self._version: Optional[str] = None
        self._available: Optional[bool] = None
        self._wiki_docs_path: Optional[Path] = None

    @property
    def vendor_path(self) -> Path:
        """Get the vendor path, auto-detecting if not set."""
        if self._vendor_path is None:
            # Try to find vendor directory relative to this module
            module_path = Path(__file__).parent.parent.parent
            self._vendor_path = module_path / "vendor" / "oelint-adv"
        return self._vendor_path

    @property
    def wiki_docs_path(self) -> Optional[Path]:
        """Get the path to wiki documentation files."""
        if self._wiki_docs_path is None:
            wiki_path = self.vendor_path / "docs" / "wiki"
            if wiki_path.is_dir():
                self._wiki_docs_path = wiki_path
        return self._wiki_docs_path

    def is_available(self) -> bool:
        """
        Check if oelint-adv is available.
        
        Returns:
            True if oelint-adv is found and can be executed.
        """
        if self._available is not None:
            return self._available

        self._available = False
        
        # Check if vendor path exists
        if not self.vendor_path.is_dir():
            return False
        
        # Check for oelint_adv module
        oelint_module = self.vendor_path / "oelint_adv"
        if not oelint_module.is_dir():
            return False
        
        # Check for venv Python
        venv_python = self.vendor_path / ".venv" / "bin" / "python"
        if venv_python.is_file():
            self._venv_python = venv_python
            self._oelint_path = self.vendor_path
            self._available = True
        else:
            # Try system Python with the module path
            # Check if we can import oelint_adv
            try:
                result = subprocess.run(
                    [sys.executable, "-c", "import oelint_adv; print(oelint_adv.__version__)"],
                    cwd=str(self.vendor_path),
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env={**os.environ, "PYTHONPATH": str(self.vendor_path)},
                )
                if result.returncode == 0:
                    self._oelint_path = self.vendor_path
                    self._available = True
                    self._version = result.stdout.strip()
            except subprocess.TimeoutExpired:
                pass
        
        return self._available

    def get_version(self) -> Optional[str]:
        """Get the oelint-adv version."""
        if self._version is not None:
            return self._version
        
        if not self.is_available():
            return None
        
        try:
            result = self._run_command(["--version"])
            if result.returncode == 0:
                # Version output is typically "oelint-adv X.Y.Z"
                self._version = result.stdout.strip()
        except Exception:
            pass
        
        return self._version

    def _run_command(self, args: List[str], **kwargs) -> subprocess.CompletedProcess:
        """
        Run oelint-adv command with the appropriate Python interpreter.
        
        Args:
            args: Command line arguments for oelint-adv
            **kwargs: Additional arguments for subprocess.run
            
        Returns:
            CompletedProcess result
        """
        if self._venv_python:
            cmd = [str(self._venv_python), "-m", "oelint_adv"] + args
        else:
            cmd = [sys.executable, "-m", "oelint_adv"] + args
            kwargs.setdefault("env", {**os.environ, "PYTHONPATH": str(self.vendor_path)})
        
        kwargs.setdefault("capture_output", True)
        kwargs.setdefault("text", True)
        kwargs.setdefault("cwd", str(self.vendor_path))
        
        return subprocess.run(cmd, **kwargs)

    def run(
        self,
        paths: List[Path],
        exclude_patterns: Optional[List[str]] = None,
        mode: str = "all",
        extra_args: Optional[List[str]] = None,
    ) -> Tuple[List[OelintResult], OelintSummary, str, str]:
        """
        Run oelint-adv on the specified paths.
        
        Args:
            paths: List of files or directories to lint
            exclude_patterns: Patterns to exclude (Note: oelint-adv doesn't have
                            native exclude support, so we filter results)
            mode: Testing mode ('fast' or 'all', default: 'all')
            extra_args: Additional command line arguments
            
        Returns:
            Tuple of (results, summary, stdout, stderr)
        """
        if not self.is_available():
            return [], OelintSummary(), "", "oelint-adv is not available"
        
        # Build command arguments
        # Note: --release is not used, oelint-adv defaults to latest
        args = [
            "--mode", mode,
            "--quiet",  # Only output findings
            "--exit-zero",  # Don't fail on lint errors
        ]
        
        if extra_args:
            args.extend(extra_args)
        
        # Add paths - expand directories to .bb and .bbappend files
        file_list = []
        for path in paths:
            if path.is_file():
                if path.suffix in ('.bb', '.bbappend', '.inc', '.bbclass', '.conf'):
                    file_list.append(str(path.resolve()))
            elif path.is_dir():
                # Recursively find all bitbake files
                for ext in ('*.bb', '*.bbappend', '*.inc'):
                    file_list.extend(str(f.resolve()) for f in path.rglob(ext))
        
        if not file_list:
            return [], OelintSummary(), "", "No files to lint"
        
        # Filter out excluded patterns
        if exclude_patterns:
            filtered_files = []
            for f in file_list:
                excluded = False
                for pattern in exclude_patterns:
                    # Simple glob-like matching
                    import fnmatch
                    if fnmatch.fnmatch(f, pattern) or fnmatch.fnmatch(Path(f).name, pattern):
                        excluded = True
                        break
                    # Also check if the pattern matches any directory component
                    if pattern.rstrip('/') in f:
                        excluded = True
                        break
                if not excluded:
                    filtered_files.append(f)
            file_list = filtered_files
        
        if not file_list:
            return [], OelintSummary(), "", "All files excluded"
        
        args.extend(file_list)
        
        # Run the command
        try:
            result = self._run_command(args, timeout=600)  # 10 minute timeout
            stdout = result.stdout
            stderr = result.stderr
        except subprocess.TimeoutExpired:
            return [], OelintSummary(), "", "oelint-adv timed out after 10 minutes"
        except Exception as e:
            return [], OelintSummary(), "", f"Error running oelint-adv: {e}"
        
        # Parse results from stderr (oelint-adv outputs findings to stderr by default)
        results = self._parse_output(stderr)
        
        # Create summary
        summary = OelintSummary.from_results(
            results,
            files_scanned=len(file_list),
            tool_version=self.get_version(),
        )
        
        return results, summary, stdout, stderr

    def _parse_output(self, output: str) -> List[OelintResult]:
        """
        Parse oelint-adv output into structured results.
        
        Args:
            output: Raw output from oelint-adv (usually stderr)
            
        Returns:
            List of OelintResult objects
        """
        results = []
        
        for line in output.strip().split('\n'):
            if not line:
                continue
            
            match = self.OUTPUT_PATTERN.match(line)
            if match:
                results.append(OelintResult(
                    file=Path(match.group('file')),
                    line=int(match.group('line')),
                    severity=match.group('severity'),
                    rule_id=match.group('rule_id'),
                    message=match.group('message').strip(),
                    extra=match.group('extra'),
                ))
        
        return results

    def get_rule_documentation(self, rule_id: str) -> Optional[str]:
        """
        Get documentation content for a rule.
        
        Looks for documentation in the wiki directory with format:
        oelint.group.rule.md
        
        Args:
            rule_id: The rule ID (e.g., 'oelint.var.mandatoryvar.HOMEPAGE')
            
        Returns:
            Markdown content of the documentation, or None if not found
        """
        if not self.wiki_docs_path:
            return None
        
        # Try exact match first
        doc_file = self.wiki_docs_path / f"{rule_id}.md"
        if doc_file.is_file():
            try:
                return doc_file.read_text(encoding='utf-8')
            except Exception:
                pass
        
        # Try without the specific variable (e.g., oelint.var.mandatoryvar for HOMEPAGE)
        parts = rule_id.split('.')
        while len(parts) > 2:
            base_rule = '.'.join(parts[:-1])
            doc_file = self.wiki_docs_path / f"{base_rule}.md"
            if doc_file.is_file():
                try:
                    return doc_file.read_text(encoding='utf-8')
                except Exception:
                    pass
            parts = parts[:-1]
        
        return None

    def get_all_rule_docs(self) -> Dict[str, str]:
        """
        Get all available rule documentation.
        
        Returns:
            Dictionary mapping rule base IDs to their documentation content
        """
        docs = {}
        if not self.wiki_docs_path:
            return docs
        
        for doc_file in self.wiki_docs_path.glob("oelint.*.md"):
            rule_id = doc_file.stem  # filename without .md
            try:
                docs[rule_id] = doc_file.read_text(encoding='utf-8')
            except Exception:
                pass
        
        return docs


# Module-level instance for convenience
_integration: Optional[OelintAdvIntegration] = None


def get_oelint_integration(vendor_path: Optional[Path] = None) -> OelintAdvIntegration:
    """
    Get the oelint-adv integration instance.
    
    Args:
        vendor_path: Optional path to vendor directory
        
    Returns:
        OelintAdvIntegration instance
    """
    global _integration
    if _integration is None or vendor_path is not None:
        _integration = OelintAdvIntegration(vendor_path)
    return _integration


def is_oelint_available() -> bool:
    """Check if oelint-adv is available."""
    return get_oelint_integration().is_available()
