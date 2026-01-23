#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bake Linter - Command Line Interface.

A production-grade linter for Yocto/OpenEmbedded recipes.

Usage:
    bake-linter [OPTIONS] PATHS...
    
Examples:
    bake-linter recipes/
    bake-linter --output json,results.json meta-layer/
    bake-linter --output html,report.html --output json,results.json .
    bake-linter --enable LICENSE001,MANDATORY001 --disable STYLE001 .
    bake-linter --ci --output json,report.json --output html,report.html recipes/

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, TextIO, Tuple

from bake_linter import __version__
from bake_linter.config import LinterConfig
from bake_linter.core.engine import LintEngine
from bake_linter.core.models import ExitCode
from bake_linter.core.registry import get_registry
from bake_linter.output.text import TextFormatter, CompactTextFormatter
from bake_linter.output.json_output import JsonFormatter, JsonLinesFormatter
from bake_linter.output.html import HtmlFormatter
from bake_linter.output.html_oelint import OelintHtmlFormatter


VALID_FORMATS = ["text", "compact", "json", "jsonl", "html"]


def parse_output_spec(spec: str) -> Tuple[str, str]:
    """
    Parse an output specification in the format 'format,filename'.
    
    Args:
        spec: Output specification string like 'json,/tmp/report.json'
        
    Returns:
        Tuple of (format, filename)
        
    Raises:
        argparse.ArgumentTypeError: If format is invalid or spec is malformed
    """
    parts = spec.split(',', 1)
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            f"Invalid output specification '{spec}'. "
            f"Expected format: 'format,filename' (e.g., 'json,report.json')"
        )
    
    fmt, filename = parts
    fmt = fmt.strip().lower()
    filename = filename.strip()
    
    if not fmt:
        raise argparse.ArgumentTypeError("Format cannot be empty")
    if not filename:
        raise argparse.ArgumentTypeError("Filename cannot be empty")
    if fmt not in VALID_FORMATS:
        raise argparse.ArgumentTypeError(
            f"Invalid format '{fmt}'. Valid formats: {', '.join(VALID_FORMATS)}"
        )
    
    return (fmt, filename)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="bake-linter",
        description="Production-grade linter for Yocto/OpenEmbedded recipes",
        epilog="For more information, see: https://github.com/99ecarvalho/bake_linter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # Version
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    
    # Paths to lint
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path(".")],
        help="Files or directories to lint (default: current directory)",
    )
    
    # Config file
    parser.add_argument(
        "--config", "-c",
        type=Path,
        help="Path to configuration file",
    )
    
    # Rule selection
    rule_group = parser.add_argument_group("rule selection")
    rule_group.add_argument(
        "--enable", "-e",
        type=lambda s: s.split(","),
        metavar="RULES",
        help="Enable specific rules (comma-separated, e.g., LICENSE001,MANDATORY001)",
    )
    rule_group.add_argument(
        "--disable", "-d",
        type=lambda s: s.split(","),
        metavar="RULES",
        help="Disable specific rules (comma-separated)",
    )
    rule_group.add_argument(
        "--enable-group",
        type=lambda s: s.split(","),
        metavar="GROUPS",
        help="Enable all rules in groups (comma-separated)",
    )
    rule_group.add_argument(
        "--disable-group",
        type=lambda s: s.split(","),
        metavar="GROUPS",
        help="Disable all rules in groups (comma-separated)",
    )
    
    # Output format
    output_group = parser.add_argument_group("output options")
    output_group.add_argument(
        "--format", "-f",
        choices=VALID_FORMATS,
        default="text",
        help="Output format for stdout (default: text)",
    )
    output_group.add_argument(
        "--output", "-o",
        type=parse_output_spec,
        action="append",
        dest="outputs",
        metavar="FORMAT,FILE",
        help=(
            "Write output to file in specified format. Can be used multiple times. "
            f"Format: 'format,filename'. Valid formats: {', '.join(VALID_FORMATS)}. "
            "Example: --output json,report.json --output html,report.html"
        ),
    )
    
    # Verbosity
    verbosity_group = parser.add_argument_group("verbosity")
    verbosity_mutex = verbosity_group.add_mutually_exclusive_group()
    verbosity_mutex.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output including context",
    )
    verbosity_mutex.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress non-error output",
    )
    
    # CI mode
    ci_group = parser.add_argument_group("CI integration")
    ci_group.add_argument(
        "--ci",
        action="store_true",
        help="CI-friendly mode (no colors, strict exit codes)",
    )
    ci_group.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    ci_group.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Treat warnings as errors (exit code 1 for warnings)",
    )
    
    # Filtering
    filter_group = parser.add_argument_group("filtering")
    filter_group.add_argument(
        "--include-autogenerated",
        action="store_true",
        help="Include autogenerated files (normally skipped)",
    )
    filter_group.add_argument(
        "--exclude",
        action="append",
        dest="exclude_patterns",
        metavar="PATTERN",
        help=(
            "Exclude directories/files matching pattern. Can be used multiple times. "
            "Supports glob patterns. "
            "Example: --exclude 'build/*' --exclude '*.bak' --exclude 'test/'"
        ),
    )
    
    # Informational
    info_group = parser.add_argument_group("information")
    info_group.add_argument(
        "--list-rules",
        action="store_true",
        help="List all available rules and exit",
    )
    info_group.add_argument(
        "--list-groups",
        action="store_true",
        help="List all rule groups and exit",
    )
    info_group.add_argument(
        "--show-config",
        action="store_true",
        help="Show effective configuration and exit",
    )
    
    return parser


def list_rules() -> None:
    """Print all available rules."""
    registry = get_registry()
    registry.discover_rules()
    
    rules = registry.get_all_rules()
    
    print(f"Available rules ({len(rules)}):\n")
    print(f"{'Rule ID':<15} {'Severity':<10} {'Enabled':<8} {'Name'}")
    print("-" * 70)
    
    for rule_id in sorted(rules.keys()):
        rule_cls = rules[rule_id]
        severity = rule_cls.default_severity.name.lower()
        enabled = "yes" if rule_cls.enabled_by_default else "no"
        print(f"{rule_id:<15} {severity:<10} {enabled:<8} {rule_cls.name}")
    
    print(f"\nGroups: {', '.join(sorted(registry.get_all_groups()))}")


def list_groups() -> None:
    """Print all rule groups."""
    registry = get_registry()
    registry.discover_rules()
    
    groups = registry.get_all_groups()
    
    print(f"Available rule groups ({len(groups)}):\n")
    
    for group in sorted(groups):
        rules = registry.get_rules_by_group(group)
        rule_ids = [r.rule_id for r in rules]
        print(f"  {group}: {', '.join(sorted(rule_ids))}")


def show_config(config: LinterConfig) -> None:
    """Print effective configuration."""
    import json
    print(json.dumps(config.to_dict(), indent=2))


def get_formatter(format_name: str, color: bool, verbose: bool, output: TextIO):
    """Get the appropriate formatter."""
    formatters = {
        "text": lambda: TextFormatter(output=output, color=color, verbose=verbose),
        "compact": lambda: CompactTextFormatter(output=output, color=False, verbose=verbose),
        "json": lambda: JsonFormatter(output=output, verbose=verbose),
        "jsonl": lambda: JsonLinesFormatter(output=output, verbose=verbose),
        "html": lambda: HtmlFormatter(output=output, verbose=verbose),
    }
    return formatters[format_name]()


def run_oelint_adv(paths: List[Path], exclude_patterns: Optional[List[str]], quiet: bool = False, debug: bool = False):
    """
    Run oelint-adv if available.
    
    Args:
        paths: Paths to lint
        exclude_patterns: Patterns to exclude
        quiet: Whether to suppress status messages
        debug: Whether to enable debug output
        
    Returns:
        Tuple of (results, summary) or (None, None) if not available
    """
    import os
    
    # Enable debug mode via environment variable if requested
    if debug:
        os.environ["BAKE_LINTER_DEBUG"] = "1"
    
    from bake_linter.core.oelint_integration import get_oelint_integration
    
    integration = get_oelint_integration()
    
    if not integration.is_available():
        if not quiet:
            print("oelint-adv is not available, skipping...", file=sys.stderr)
        return None, None
    
    if not quiet:
        version = integration.get_version() or "unknown"
        print(f"Running oelint-adv ({version})...", file=sys.stderr)
    
    results, summary, _stdout, stderr = integration.run(
        paths=paths,
        exclude_patterns=exclude_patterns,
        mode="all",  # Use 'all' mode for comprehensive checking
    )
    
    if not quiet:
        if summary:
            print(f"oelint-adv found {summary.total_issues} issue(s)", file=sys.stderr)
        if stderr and not results and "not available" not in stderr.lower():
            print(f"oelint-adv stderr: {stderr[:200]}", file=sys.stderr)
    
    return results, summary


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Handle informational commands
    if args.list_rules:
        list_rules()
        return ExitCode.SUCCESS
    
    if args.list_groups:
        list_groups()
        return ExitCode.SUCCESS
    
    # Load configuration
    try:
        config = LinterConfig.load(args.config)
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return ExitCode.RUNTIME_ERROR
    
    # Report config file status (unless quiet mode)
    if not args.quiet:
        if config.config_file:
            print(f"Using config: {config.config_file}")
        else:
            print("No config file found, using defaults.")
    
    # Merge CLI arguments
    config.merge_cli_args(
        enable=args.enable,
        disable=args.disable,
        enable_groups=args.enable_group,
        disable_groups=args.disable_group,
        output_format=args.format,
        output_file=None,  # No longer using single output file
        verbose=args.verbose,
        quiet=args.quiet,
        color=not args.no_color,
        ci_mode=args.ci,
    )
    
    if args.show_config:
        show_config(config)
        return ExitCode.SUCCESS
    
    # Validate paths
    for path in args.paths:
        if not path.exists():
            print(f"Error: Path does not exist: {path}", file=sys.stderr)
            return ExitCode.RUNTIME_ERROR
    
    # Combine exclude patterns from config and CLI
    exclude_patterns = list(config.exclude_patterns)
    if args.exclude_patterns:
        exclude_patterns.extend(args.exclude_patterns)
    
    # Initialize engine
    engine = LintEngine()
    
    # Configure engine
    engine.configure(
        rule_configs=config.get_rule_configs(),
        enabled_rules=list(config.enabled_rules) if config.enabled_rules else None,
        disabled_rules=list(config.disabled_rules),
        enabled_groups=config.enabled_groups,
        disabled_groups=config.disabled_groups,
        skip_autogenerated=not args.include_autogenerated,
        exclude_patterns=exclude_patterns if exclude_patterns else None,
    )
    
    # Run lint
    try:
        results = engine.lint_files(args.paths)
    except Exception as e:
        import traceback
        print(f"Lint error: {e}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc()
        return ExitCode.RUNTIME_ERROR
    
    summary = engine.get_summary()
    
    # Run oelint-adv if available
    # Enable debug mode in CI to help diagnose issues
    oelint_results, oelint_summary = run_oelint_adv(
        paths=args.paths,
        exclude_patterns=exclude_patterns if exclude_patterns else None,
        quiet=config.quiet,
        debug=args.ci,  # Enable debug output in CI mode
    )
    
    # Output to stdout using the primary format
    use_color = config.color and not args.ci and sys.stdout.isatty()
    if not config.quiet:
        formatter = get_formatter(
            args.format,
            color=use_color,
            verbose=args.verbose,
            output=sys.stdout,
        )
        # Set oelint-adv data if available
        if oelint_results is not None and oelint_summary is not None:
            formatter.set_oelint_data(oelint_results, oelint_summary)
        formatter.write(results, summary)
    
    # Generate additional output files if specified
    if args.outputs:
        for fmt, filename in args.outputs:
            try:
                filepath = Path(filename)
                # Create parent directories if needed
                filepath.parent.mkdir(parents=True, exist_ok=True)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    file_formatter = get_formatter(
                        fmt,
                        color=False,  # No color for file outputs
                        verbose=args.verbose,
                        output=f,
                    )
                    # Set oelint-adv data if available
                    if oelint_results is not None and oelint_summary is not None:
                        file_formatter.set_oelint_data(oelint_results, oelint_summary)
                    file_formatter.write(results, summary)
                
                if not config.quiet:
                    print(f"\n{fmt.upper()} report written to: {filepath}", file=sys.stderr)
                
                # For HTML output, also generate separate oelint-adv HTML file if results available
                if fmt == "html" and oelint_results is not None and oelint_summary is not None:
                    # Generate filename with _oelintadv suffix
                    oelint_filepath = filepath.with_stem(filepath.stem + "_oelintadv")
                    
                    try:
                        with open(oelint_filepath, "w", encoding="utf-8") as of:
                            oelint_formatter = OelintHtmlFormatter(
                                output=of,
                                verbose=args.verbose,
                                title="oelint-adv Report",
                            )
                            oelint_formatter.write(oelint_results, oelint_summary)
                        
                        if not config.quiet:
                            print(f"oelint-adv HTML report written to: {oelint_filepath}", file=sys.stderr)
                    except IOError as e:
                        print(f"Error writing oelint-adv HTML output to {oelint_filepath}: {e}", file=sys.stderr)
                        # Don't fail the whole run for this, just warn
                        
            except IOError as e:
                print(f"Error writing {fmt} output to {filename}: {e}", file=sys.stderr)
                return ExitCode.RUNTIME_ERROR
    
    # Determine exit code
    exit_code = summary.get_exit_code()
    
    # Treat warnings as errors if requested
    if args.warnings_as_errors and exit_code == ExitCode.WARNINGS_FOUND:
        exit_code = ExitCode.ERRORS_FOUND
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
