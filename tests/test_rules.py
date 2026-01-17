"""
Unit tests for lint rules.
"""

import pytest
from pathlib import Path
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext, VariableAssignment
from bake_linter.core.registry import RuleRegistry, get_registry
from bake_linter.rules.license import LicenseRequiredRule, LicenseTypoRule, LicFilesChkSumRule
from bake_linter.rules.mandatory import SummaryDescriptionRule, SrcUriRule, InheritCheck
from bake_linter.rules.deprecated import DeprecatedOverrideSyntaxRule
from bake_linter.rules.naming import RecipeNamingRule
from bake_linter.rules.style import EmptyVariableRule, DuplicateInheritRule
from bake_linter.rules.security import InsecureUriRule


class TestLicenseRules:
    """Tests for license-related rules."""

    def test_license_required_missing(self):
        """Test that missing LICENSE is flagged."""
        context = FileContext(
            path=Path("test_1.0.bb"),
            content='SUMMARY = "Test"',
            lines=['SUMMARY = "Test"'],
            variables={"SUMMARY": [VariableAssignment("SUMMARY", "Test", 1)]},
        )
        
        rule = LicenseRequiredRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "LICENSE001"
        assert results[0].severity == Severity.ERROR
        assert "LICENSE" in results[0].message

    def test_license_required_present(self):
        """Test that present LICENSE passes."""
        context = FileContext(
            path=Path("test_1.0.bb"),
            content='LICENSE = "MIT"',
            lines=['LICENSE = "MIT"'],
            variables={"LICENSE": [VariableAssignment("LICENSE", "MIT", 1)]},
        )
        
        rule = LicenseRequiredRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_license_typo_detected(self):
        """Test that LICENSE typos are detected."""
        context = FileContext(
            path=Path("test_1.0.bb"),
            content='LICENSEX = "MIT"',
            lines=['LICENSEX = "MIT"'],
            variables={"LICENSEX": [VariableAssignment("LICENSEX", "MIT", 1)]},
        )
        
        rule = LicenseTypoRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "LICENSE002"
        assert "LICENSEX" in results[0].message

    def test_lic_files_chksum_warning(self):
        """Test that missing LIC_FILES_CHKSUM for non-CLOSED is warned."""
        context = FileContext(
            path=Path("test_1.0.bb"),
            content='LICENSE = "MIT"',
            lines=['LICENSE = "MIT"'],
            variables={"LICENSE": [VariableAssignment("LICENSE", "MIT", 1)]},
        )
        
        rule = LicFilesChkSumRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "LICENSE003"

    def test_lic_files_chksum_closed_ok(self):
        """Test that CLOSED license doesn't need LIC_FILES_CHKSUM."""
        context = FileContext(
            path=Path("test_1.0.bb"),
            content='LICENSE = "CLOSED"',
            lines=['LICENSE = "CLOSED"'],
            variables={"LICENSE": [VariableAssignment("LICENSE", "CLOSED", 1)]},
        )
        
        rule = LicFilesChkSumRule()
        results = rule.check(context)
        
        assert len(results) == 0


class TestMandatoryRules:
    """Tests for mandatory variable rules."""

    def test_summary_missing(self):
        """Test that missing SUMMARY/DESCRIPTION is flagged."""
        context = FileContext(
            path=Path("test_1.0.bb"),
            content='LICENSE = "MIT"',
            lines=['LICENSE = "MIT"'],
            variables={"LICENSE": [VariableAssignment("LICENSE", "MIT", 1)]},
        )
        
        rule = SummaryDescriptionRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "MANDATORY001"

    def test_summary_present(self):
        """Test that present SUMMARY passes."""
        context = FileContext(
            path=Path("test_1.0.bb"),
            content='SUMMARY = "Test"',
            lines=['SUMMARY = "Test"'],
            variables={"SUMMARY": [VariableAssignment("SUMMARY", "Test", 1)]},
        )
        
        rule = SummaryDescriptionRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_inherit_check_packagegroup(self):
        """Test that packagegroup- recipe needs inherit packagegroup."""
        context = FileContext(
            path=Path("packagegroup-test.bb"),
            content='LICENSE = "MIT"',
            lines=['LICENSE = "MIT"'],
            variables={"LICENSE": [VariableAssignment("LICENSE", "MIT", 1)]},
        )
        
        rule = InheritCheck()
        results = rule.check(context)
        
        assert len(results) == 1
        assert "packagegroup" in results[0].message.lower()


class TestDeprecatedRules:
    """Tests for deprecated syntax rules."""

    def test_deprecated_append_syntax(self):
        """Test that old _append syntax is flagged."""
        context = FileContext(
            path=Path("test_1.0.bb"),
            content='RDEPENDS_${PN} += "foo"',
            lines=['RDEPENDS_${PN} += "foo"'],
            variables={},
        )
        
        rule = DeprecatedOverrideSyntaxRule()
        results = rule.check(context)
        
        # Should flag the underscore override
        assert len(results) >= 1
        assert results[0].rule_id == "DEPRECATED001"


class TestNamingRules:
    """Tests for naming convention rules."""

    def test_recipe_missing_version(self):
        """Test that recipe without version is flagged."""
        context = FileContext(
            path=Path("myrecipe.bb"),
            content='LICENSE = "MIT"',
            lines=['LICENSE = "MIT"'],
            variables={},
        )
        
        rule = RecipeNamingRule()
        results = rule.check(context)
        
        assert any("version" in r.message.lower() for r in results)


class TestStyleRules:
    """Tests for style rules."""

    def test_duplicate_inherit(self):
        """Test that duplicate inherit is flagged."""
        context = FileContext(
            path=Path("test_1.0.bb"),
            content='inherit foo\ninherit foo',
            lines=['inherit foo', 'inherit foo'],
            variables={},
        )
        
        rule = DuplicateInheritRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "STYLE006"
        assert "duplicate" in results[0].message.lower()

    def test_package_list_format_alphabetical(self):
        """Test that non-alphabetical package lists are flagged."""
        from bake_linter.rules.style import PackageListFormatRule
        
        content = '''IMAGE_INSTALL:append = " \\
    zebra-pkg \\
    alpha-pkg \\
"
'''
        context = FileContext(
            path=Path("test-image.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = PackageListFormatRule()
        results = rule.check(context)
        
        # Should flag alphabetical order issue
        alpha_issues = [r for r in results if "alphabetical" in r.message.lower()]
        assert len(alpha_issues) >= 1
        assert alpha_issues[0].rule_id == "STYLE007"

    def test_package_list_format_correct(self):
        """Test that correctly formatted package lists pass."""
        from bake_linter.rules.style import PackageListFormatRule
        
        content = '''IMAGE_INSTALL:append = " \\
    alpha-pkg \\
    beta-pkg \\
    zebra-pkg \\
"

'''
        context = FileContext(
            path=Path("test-image.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = PackageListFormatRule()
        results = rule.check(context)
        
        # Should have no issues (alphabetical and has blank line after)
        assert len(results) == 0

    def test_package_list_missing_blank_line(self):
        """Test that missing blank line after closing quote is flagged."""
        from bake_linter.rules.style import PackageListFormatRule
        
        content = '''IMAGE_INSTALL:append = " \\
    alpha-pkg \\
"
ANOTHER_VAR = "value"
'''
        context = FileContext(
            path=Path("test-image.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = PackageListFormatRule()
        results = rule.check(context)
        
        # Should flag missing blank line
        blank_issues = [r for r in results if "blank line" in r.message.lower()]
        assert len(blank_issues) >= 1

    def test_systemd_auto_enable_without_pn(self):
        """Test that SYSTEMD_AUTO_ENABLE without :${PN} is flagged."""
        from bake_linter.rules.style import SystemdAutoEnableRule
        
        content = '''inherit systemd
SYSTEMD_AUTO_ENABLE = "enable"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdAutoEnableRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "STYLE008"
        assert ":${PN}" in results[0].message

    def test_systemd_auto_enable_with_pn_ok(self):
        """Test that SYSTEMD_AUTO_ENABLE:${PN} passes."""
        from bake_linter.rules.style import SystemdAutoEnableRule
        
        content = '''inherit systemd
SYSTEMD_AUTO_ENABLE:${PN} = "enable"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdAutoEnableRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_install_dir_missing_trailing_slash(self):
        """Test that install to directory without trailing slash is flagged."""
        from bake_linter.rules.style import InstallDirectoryTrailingSlashRule
        
        content = '''do_install() {
    install -m 0644 ${WORKDIR}/file.service ${D}${systemd_system_unitdir}
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = InstallDirectoryTrailingSlashRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "STYLE009"
        assert "trailing" in results[0].hint.lower()

    def test_install_dir_with_trailing_slash_ok(self):
        """Test that install to directory with trailing slash passes."""
        from bake_linter.rules.style import InstallDirectoryTrailingSlashRule
        
        content = '''do_install() {
    install -m 0644 ${WORKDIR}/file.service ${D}${systemd_system_unitdir}/
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = InstallDirectoryTrailingSlashRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_systemd_redundant_files_flagged(self):
        """Test that redundant FILES with systemd is flagged."""
        from bake_linter.rules.style import SystemdRedundantFilesRule
        
        content = '''inherit systemd
FILES:${PN} += "${systemd_system_unitdir}/*.service"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdRedundantFilesRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "STYLE010"
        assert "redundant" in results[0].message.lower()

    def test_systemd_redundant_files_no_inherit_ok(self):
        """Test that FILES without systemd inherit is not flagged."""
        from bake_linter.rules.style import SystemdRedundantFilesRule
        
        content = '''FILES:${PN} += "${systemd_system_unitdir}/*.service"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdRedundantFilesRule()
        results = rule.check(context)
        
        # No inherit systemd, so no flag
        assert len(results) == 0

class TestSecurityRules:
    """Tests for security rules."""

    def test_insecure_http_uri(self):
        """Test that HTTP URI is flagged."""
        context = FileContext(
            path=Path("test_1.0.bb"),
            content='SRC_URI = "http://example.com/foo.tar.gz"',
            lines=['SRC_URI = "http://example.com/foo.tar.gz"'],
            variables={"SRC_URI": [VariableAssignment("SRC_URI", "http://example.com/foo.tar.gz", 1)]},
        )
        
        rule = InsecureUriRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "SECURITY001"


class TestRuleRegistry:
    """Tests for rule registry functionality."""

    def test_rule_discovery(self):
        """Test that rules are discovered."""
        registry = get_registry()
        count = registry.discover_rules()
        
        assert count > 0
        assert "LICENSE001" in registry.get_rule_ids()

    def test_get_rules_by_group(self):
        """Test getting rules by group."""
        registry = get_registry()
        registry.discover_rules()
        
        license_rules = registry.get_rules_by_group("license")
        assert len(license_rules) > 0
        
        rule_ids = [r.rule_id for r in license_rules]
        assert "LICENSE001" in rule_ids
