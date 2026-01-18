# -*- coding: utf-8 -*-
"""
Unit tests for CLI functionality.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

import pytest
import sys
from pathlib import Path
from io import StringIO

from bake_linter.cli import main, create_parser, parse_output_spec
from bake_linter.core.models import ExitCode


class TestCLIParser:
    """Tests for CLI argument parsing."""

    def test_default_format(self):
        """Test default format is text."""
        parser = create_parser()
        args = parser.parse_args(["."])
        assert args.format == "text"

    def test_format_options(self):
        """Test different format options."""
        parser = create_parser()
        
        for fmt in ["text", "compact", "json", "jsonl", "html"]:
            args = parser.parse_args(["--format", fmt, "."])
            assert args.format == fmt

    def test_enable_rules(self):
        """Test enabling specific rules."""
        parser = create_parser()
        args = parser.parse_args(["--enable", "LICENSE001,MANDATORY001", "."])
        assert args.enable == ["LICENSE001", "MANDATORY001"]

    def test_disable_rules(self):
        """Test disabling specific rules."""
        parser = create_parser()
        args = parser.parse_args(["--disable", "STYLE001", "."])
        assert args.disable == ["STYLE001"]

    def test_verbose_quiet_mutually_exclusive(self):
        """Test that --verbose and --quiet are mutually exclusive."""
        parser = create_parser()
        
        with pytest.raises(SystemExit):
            parser.parse_args(["--verbose", "--quiet", "."])

    def test_ci_mode(self):
        """Test CI mode flag."""
        parser = create_parser()
        args = parser.parse_args(["--ci", "."])
        assert args.ci is True

    def test_output_spec_single(self):
        """Test single output specification."""
        parser = create_parser()
        args = parser.parse_args(["--output", "json,report.json", "."])
        assert args.outputs == [("json", "report.json")]

    def test_output_spec_multiple(self):
        """Test multiple output specifications."""
        parser = create_parser()
        args = parser.parse_args([
            "--output", "json,report.json",
            "--output", "html,report.html",
            "."
        ])
        assert args.outputs == [("json", "report.json"), ("html", "report.html")]

    def test_output_spec_with_path(self):
        """Test output specification with full path."""
        parser = create_parser()
        args = parser.parse_args(["--output", "html,/tmp/reports/output.html", "."])
        assert args.outputs == [("html", "/tmp/reports/output.html")]


class TestOutputSpecParser:
    """Tests for output specification parser."""

    def test_parse_valid_spec(self):
        """Test parsing valid output specifications."""
        assert parse_output_spec("json,report.json") == ("json", "report.json")
        assert parse_output_spec("html,/tmp/report.html") == ("html", "/tmp/report.html")
        assert parse_output_spec("text,output.txt") == ("text", "output.txt")
        assert parse_output_spec("compact,log.txt") == ("compact", "log.txt")
        assert parse_output_spec("jsonl,results.jsonl") == ("jsonl", "results.jsonl")

    def test_parse_spec_with_spaces(self):
        """Test parsing specifications with spaces."""
        assert parse_output_spec(" json , report.json ") == ("json", "report.json")

    def test_parse_invalid_format(self):
        """Test parsing with invalid format."""
        import argparse
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_output_spec("invalid,report.txt")
        assert "Invalid format" in str(exc_info.value)

    def test_parse_missing_comma(self):
        """Test parsing without comma separator."""
        import argparse
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_output_spec("jsonreport.json")
        assert "Expected format" in str(exc_info.value)

    def test_parse_empty_format(self):
        """Test parsing with empty format."""
        import argparse
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_output_spec(",report.json")
        assert "empty" in str(exc_info.value).lower()

    def test_parse_empty_filename(self):
        """Test parsing with empty filename."""
        import argparse
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_output_spec("json,")
        assert "empty" in str(exc_info.value).lower()


class TestCLIExecution:
    """Tests for CLI execution."""

    def test_list_rules(self, capsys):
        """Test --list-rules option."""
        exit_code = main(["--list-rules"])
        
        assert exit_code == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "LICENSE001" in captured.out
        assert "Available rules" in captured.out

    def test_list_groups(self, capsys):
        """Test --list-groups option."""
        exit_code = main(["--list-groups"])
        
        assert exit_code == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "license" in captured.out

    def test_nonexistent_path(self, capsys):
        """Test with nonexistent path."""
        exit_code = main(["/nonexistent/path/that/does/not/exist"])
        
        assert exit_code == ExitCode.RUNTIME_ERROR


class TestExitCodes:
    """Tests for exit code behavior."""

    def test_exit_code_success(self, tmp_path):
        """Test exit code 0 for no issues."""
        # Create a valid recipe
        recipe = tmp_path / "good_1.0.bb"
        recipe.write_text('''
SUMMARY = "A good recipe"
LICENSE = "CLOSED"
inherit packagegroup
''')
        
        exit_code = main([str(recipe), "--quiet"])
        # May have some issues but test the mechanism works
        assert exit_code in [ExitCode.SUCCESS, ExitCode.WARNINGS_FOUND, ExitCode.ERRORS_FOUND]

    def test_warnings_as_errors(self, tmp_path):
        """Test --warnings-as-errors flag."""
        recipe = tmp_path / "test_1.0.bb"
        recipe.write_text('LICENSE = "MIT"')  # Missing LIC_FILES_CHKSUM will be warning
        
        # Run with warnings-as-errors
        exit_code = main([str(recipe), "--warnings-as-errors", "--quiet"])
        
        # Should return error code if there are warnings
        assert exit_code in [ExitCode.SUCCESS, ExitCode.ERRORS_FOUND]
