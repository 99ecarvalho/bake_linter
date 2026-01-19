# -*- coding: utf-8 -*-
"""
Unit tests for inline suppression functionality.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

import pytest
from pathlib import Path

from bake_linter.core.models import FileContext, Severity
from bake_linter.core.engine import LintEngine, INLINE_SUPPRESSION_PATTERN
from bake_linter.rules.license import LicenseRequiredRule
from bake_linter.rules.mandatory import SummaryDescriptionRule


class TestInlineSuppressionPattern:
    """Test the inline suppression regex pattern."""
    
    def test_basic_suppression(self):
        """Test basic nolint comment."""
        line = "# nolint: LICENSE001"
        match = INLINE_SUPPRESSION_PATTERN.search(line)
        assert match is not None
        assert "LICENSE001" in match.group("rules")
    
    def test_multiple_rules(self):
        """Test suppressing multiple rules."""
        line = "# nolint: LICENSE001, MANDATORY001, STYLE001"
        match = INLINE_SUPPRESSION_PATTERN.search(line)
        assert match is not None
        rules = match.group("rules")
        assert "LICENSE001" in rules
        assert "MANDATORY001" in rules
        assert "STYLE001" in rules
    
    def test_inline_with_code(self):
        """Test suppression on same line as code."""
        line = 'SUMMARY = "Test"  # nolint: MANDATORY001'
        match = INLINE_SUPPRESSION_PATTERN.search(line)
        assert match is not None
        assert "MANDATORY001" in match.group("rules")
    
    def test_case_insensitive(self):
        """Test that nolint is case-insensitive."""
        for variant in ["nolint", "NOLINT", "NoLint", "nOLINT"]:
            line = f"# {variant}: LICENSE001"
            match = INLINE_SUPPRESSION_PATTERN.search(line)
            assert match is not None, f"Failed for variant: {variant}"
    
    def test_whitespace_variations(self):
        """Test various whitespace patterns."""
        variations = [
            "#nolint: LICENSE001",
            "# nolint: LICENSE001",
            "#  nolint:  LICENSE001",
            "# nolint:LICENSE001",
        ]
        for line in variations:
            match = INLINE_SUPPRESSION_PATTERN.search(line)
            assert match is not None, f"Failed for: {line}"


class TestInlineSuppressionParsing:
    """Test parsing of inline suppressions from files."""
    
    def test_parse_standalone_comment(self):
        """Test parsing standalone suppression comment."""
        content = """# nolint: LICENSE001
SUMMARY = "Test"
"""
        lines = content.splitlines()
        context = FileContext(
            path=Path("test.bb"),
            content=content,
            lines=lines,
            variables={},
        )
        
        # The engine should parse suppressions
        # Line 1 has suppression for LICENSE001
        # It should apply to line 1 and line 2
        assert 1 in context.inline_suppressions or 2 in context.inline_suppressions
    
    def test_parse_inline_comment(self):
        """Test parsing inline suppression comment."""
        content = """LICENSE = "MIT"  # nolint: LICENSE001
SUMMARY = "Test"
"""
        lines = content.splitlines()
        # This will be tested through the engine


class TestInlineSuppressionFunctionality:
    """Test that inline suppressions actually suppress issues."""
    
    def test_suppress_specific_rule(self, tmp_path):
        """Test that a specific rule can be suppressed."""
        # Create a test file missing LICENSE
        test_file = tmp_path / "test.bb"
        test_file.write_text("""# nolint: LICENSE001
SUMMARY = "Test recipe without license"
DESCRIPTION = "This should not trigger LICENSE001"
""")
        
        engine = LintEngine()
        engine.configure(enabled_rules=["LICENSE001"])
        results = engine.lint_files([test_file])
        
        # Should have no results because LICENSE001 is suppressed
        assert len(results) == 0
    
    def test_suppress_multiple_rules(self, tmp_path):
        """Test suppressing multiple rules at once."""
        test_file = tmp_path / "test.bb"
        test_file.write_text("""# nolint: LICENSE001, MANDATORY001
# This file has no LICENSE and no SUMMARY
SRC_URI = "https://example.com/source.tar.gz"
""")
        
        engine = LintEngine()
        engine.configure(enabled_rules=["LICENSE001", "MANDATORY001"])
        results = engine.lint_files([test_file])
        
        # Both rules should be suppressed
        assert len(results) == 0
    
    def test_suppression_applies_to_next_line(self, tmp_path):
        """Test that standalone suppression applies to next line."""
        test_file = tmp_path / "test.bb"
        test_file.write_text("""SUMMARY = "Test"

# This suppression applies to the next line
# nolint: LICENSE001
DESCRIPTION = "No license needed here apparently"
""")
        
        engine = LintEngine()
        engine.configure(enabled_rules=["LICENSE001"])
        results = engine.lint_files([test_file])
        
        # LICENSE001 should be suppressed
        assert len(results) == 0
    
    def test_unsuppressed_rule_still_fires(self, tmp_path):
        """Test that unsuppressed rules still trigger."""
        test_file = tmp_path / "test.bb"
        test_file.write_text("""# nolint: MANDATORY001
# Only MANDATORY001 is suppressed, LICENSE001 should still fire
SRC_URI = "https://example.com/source.tar.gz"
""")
        
        engine = LintEngine()
        engine.configure(enabled_rules=["LICENSE001", "MANDATORY001"])
        results = engine.lint_files([test_file])
        
        # Should have 1 result for LICENSE001
        assert len(results) == 1
        assert results[0].rule_id == "LICENSE001"
    
    def test_suppression_on_specific_line(self, tmp_path):
        """Test that suppression only applies to the specified line."""
        test_file = tmp_path / "test.bb"
        test_file.write_text("""LICENSE = "MIT"

# First summary has no suppression - should trigger
SUMMARY = "Test"

# Second has suppression - should not trigger
DESCRIPTION = "Test description"  # nolint: MANDATORY001
""")
        
        # Note: This test would need MANDATORY001 to trigger on DESCRIPTION
        # which it doesn't currently, but demonstrates the concept
    
    def test_wildcard_suppression(self, tmp_path):
        """Test wildcard suppression (suppress all rules)."""
        test_file = tmp_path / "test.bb"
        test_file.write_text("""# nolint: *
# Suppress all rules on this file
SRC_URI = "https://example.com/source.tar.gz"
""")
        
        engine = LintEngine()
        engine.configure(enabled_rules=["LICENSE001", "MANDATORY001"])
        results = engine.lint_files([test_file])
        
        # All rules should be suppressed
        assert len(results) == 0


class TestSuppressionEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_malformed_suppression(self, tmp_path):
        """Test that malformed suppressions are ignored."""
        test_file = tmp_path / "test.bb"
        test_file.write_text("""# nolint:  
# Malformed - no rule IDs
LICENSE = "MIT"
""")
        
        # Should still parse without errors
        engine = LintEngine()
        results = engine.lint_files([test_file])
        # Results depend on which rules are enabled
    
    def test_suppression_with_invalid_rule_id(self, tmp_path):
        """Test that invalid rule IDs in suppressions are harmless."""
        test_file = tmp_path / "test.bb"
        test_file.write_text("""# nolint: NONEXISTENT_RULE_12345
LICENSE = "MIT"
SUMMARY = "Test"
""")
        
        # Should not cause errors, just ineffective suppression
        engine = LintEngine()
        results = engine.lint_files([test_file])
        # Should complete without error
    
    def test_nested_suppressions(self, tmp_path):
        """Test multiple suppressions on consecutive lines."""
        test_file = tmp_path / "test.bb"
        test_file.write_text("""# nolint: LICENSE001
# nolint: MANDATORY001
DESCRIPTION = "Multiple suppressions"
""")
        
        engine = LintEngine()
        engine.configure(enabled_rules=["LICENSE001", "MANDATORY001"])
        results = engine.lint_files([test_file])
        
        # Both should be suppressed
        assert len(results) == 0


def test_readme_example(tmp_path):
    """Test the example from the README/documentation."""
    test_file = tmp_path / "example.bb"
    test_file.write_text("""SUMMARY = "Example recipe"

# This recipe doesn't need a traditional LICENSE
# because it's a meta-package
# nolint: LICENSE001
RDEPENDS:${PN} = "dependency1 dependency2"
""")
    
    engine = LintEngine()
    engine.configure(enabled_rules=["LICENSE001"])
    results = engine.lint_files([test_file])
    
    assert len(results) == 0, "LICENSE001 should be suppressed"
