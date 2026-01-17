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

    def test_service_files_not_in_files_flagged(self):
        """Test that service files installed to non-standard locations without FILES are flagged."""
        from bake_linter.rules.style import SystemdRedundantFilesRule
        
        content = '''do_install() {
    install -m 0644 ${WORKDIR}/custom.service ${D}/custom/location/
}
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
        assert "not be packaged" in results[0].message.lower() or "non-standard" in results[0].message.lower()

    def test_service_files_in_standard_location_ok(self):
        """Test that service files in standard locations are not flagged."""
        from bake_linter.rules.style import SystemdRedundantFilesRule
        
        content = '''do_install() {
    install -m 0644 ${WORKDIR}/my.service ${D}${systemd_system_unitdir}/
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdRedundantFilesRule()
        results = rule.check(context)
        
        # Standard location, no flag needed
        assert len(results) == 0

    def test_service_files_with_explicit_files_ok(self):
        """Test that service files with explicit FILES entry are not flagged."""
        from bake_linter.rules.style import SystemdRedundantFilesRule
        
        content = '''do_install() {
    install -m 0644 ${WORKDIR}/custom.service ${D}/custom/location/
}
FILES:${PN} += "/custom/location/custom.service"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdRedundantFilesRule()
        results = rule.check(context)
        
        # Has explicit FILES entry, no flag
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

    def test_insecure_ftp_uri(self):
        """Test that FTP URI is flagged."""
        context = FileContext(
            path=Path("test_1.0.bb"),
            content='SRC_URI = "ftp://example.com/foo.tar.gz"',
            lines=['SRC_URI = "ftp://example.com/foo.tar.gz"'],
            variables={},
        )
        
        rule = InsecureUriRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert "ftp" in results[0].message.lower()

    def test_insecure_git_protocol(self):
        """Test that git:// protocol is flagged."""
        context = FileContext(
            path=Path("test_1.0.bb"),
            content='SRC_URI = "git://github.com/user/repo.git"',
            lines=['SRC_URI = "git://github.com/user/repo.git"'],
            variables={},
        )
        
        rule = InsecureUriRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert "git://" in results[0].message


class TestSystemdRules:
    """Tests for systemd-related rules."""

    def test_systemd_without_inherit(self):
        """Test that systemd usage without inherit is flagged."""
        from bake_linter.rules.systemd import SystemdWithoutInheritRule
        
        content = '''do_install() {
    install -d ${D}${systemd_system_unitdir}
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdWithoutInheritRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "SYSTEMD001"

    def test_systemd_with_inherit_ok(self):
        """Test that systemd usage with inherit passes."""
        from bake_linter.rules.systemd import SystemdWithoutInheritRule
        
        content = '''inherit systemd

do_install() {
    install -d ${D}${systemd_system_unitdir}
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdWithoutInheritRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_systemd_hardcoded_paths(self):
        """Test that hardcoded systemd paths are flagged."""
        from bake_linter.rules.systemd import SystemdHardcodedPathsRule
        
        content = '''do_install() {
    install -d ${D}/lib/systemd/system
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdHardcodedPathsRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "SYSTEMD003"


class TestInstallRules:
    """Tests for install-related rules."""

    def test_cp_instead_of_install(self):
        """Test that cp in do_install is flagged."""
        from bake_linter.rules.install import CpInsteadOfInstallRule
        
        content = '''do_install() {
    cp myfile ${D}${bindir}/
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = CpInsteadOfInstallRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "INSTALL001"

    def test_install_without_mode(self):
        """Test that install without -m is flagged."""
        from bake_linter.rules.install import InstallWithoutModeRule
        
        content = '''do_install() {
    install myfile ${D}${bindir}/
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = InstallWithoutModeRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "INSTALL002"

    def test_install_with_mode_ok(self):
        """Test that install with -m passes."""
        from bake_linter.rules.install import InstallWithoutModeRule
        
        content = '''do_install() {
    install -m 0755 myfile ${D}${bindir}/
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = InstallWithoutModeRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_install_d_without_mode_ok(self):
        """Test that install -d without -m passes (directory creation)."""
        from bake_linter.rules.install import InstallWithoutModeRule
        
        content = '''do_install() {
    install -d ${D}${bindir}
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = InstallWithoutModeRule()
        results = rule.check(context)
        
        assert len(results) == 0


class TestBbappendRules:
    """Tests for bbappend-related rules."""

    def test_missing_filesextrapaths(self):
        """Test that missing FILESEXTRAPATHS is flagged."""
        from bake_linter.rules.bbappend import MissingFilesextrapathsRule
        
        content = '''SRC_URI += "file://myconfig.conf"
'''
        context = FileContext(
            path=Path("test_1.0.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MissingFilesextrapathsRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "BBAPPEND001"

    def test_with_filesextrapaths_ok(self):
        """Test that FILESEXTRAPATHS set passes."""
        from bake_linter.rules.bbappend import MissingFilesextrapathsRule
        
        content = '''FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://myconfig.conf"
'''
        context = FileContext(
            path=Path("test_1.0.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MissingFilesextrapathsRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_task_override_without_suffix(self):
        """Test that task override without :append is flagged."""
        from bake_linter.rules.bbappend import TaskOverrideWithoutSuffixRule
        
        content = '''do_install() {
    install -m 0644 myfile ${D}${sysconfdir}/
}
'''
        context = FileContext(
            path=Path("test_1.0.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = TaskOverrideWithoutSuffixRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "BBAPPEND002"

    def test_task_append_ok(self):
        """Test that task :append passes."""
        from bake_linter.rules.bbappend import TaskOverrideWithoutSuffixRule
        
        content = '''do_install:append() {
    install -m 0644 myfile ${D}${sysconfdir}/
}
'''
        context = FileContext(
            path=Path("test_1.0.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = TaskOverrideWithoutSuffixRule()
        results = rule.check(context)
        
        assert len(results) == 0


class TestDependencyRules:
    """Tests for dependency-related rules."""

    def test_native_in_rdepends(self):
        """Test that -native in RDEPENDS is flagged."""
        from bake_linter.rules.dependency import WrongDependencyTypeRule
        
        content = '''RDEPENDS:${PN} += "cmake-native"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = WrongDependencyTypeRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "DEPENDENCY001"

    def test_build_tool_in_rdepends(self):
        """Test that build tools in RDEPENDS are flagged."""
        from bake_linter.rules.dependency import WrongDependencyTypeRule
        
        content = '''RDEPENDS:${PN} += "cmake pkgconfig"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = WrongDependencyTypeRule()
        results = rule.check(context)
        
        assert len(results) >= 1


class TestPatchRules:
    """Tests for patch-related rules."""

    def test_patch_without_striplevel(self):
        """Test that patch without striplevel is flagged."""
        from bake_linter.rules.patch import PatchWithoutStriplevelRule
        
        content = '''SRC_URI += "file://fix-build.patch"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = PatchWithoutStriplevelRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "PATCH001"

    def test_patch_with_striplevel_ok(self):
        """Test that patch with striplevel passes."""
        from bake_linter.rules.patch import PatchWithoutStriplevelRule
        
        content = '''SRC_URI += "file://fix-build.patch;striplevel=1"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = PatchWithoutStriplevelRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_srcrev_autorev(self):
        """Test that AUTOREV is flagged."""
        from bake_linter.rules.patch import SrcrevUnpinnedRule
        
        content = '''SRCREV = "${AUTOREV}"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SrcrevUnpinnedRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "SRCREV001"

    def test_srcrev_master(self):
        """Test that branch name in SRCREV is flagged."""
        from bake_linter.rules.patch import SrcrevUnpinnedRule
        
        content = '''SRCREV = "master"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SrcrevUnpinnedRule()
        results = rule.check(context)
        
        assert len(results) == 1

    def test_srcrev_pinned_ok(self):
        """Test that pinned SRCREV passes."""
        from bake_linter.rules.patch import SrcrevUnpinnedRule
        
        content = '''SRCREV = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SrcrevUnpinnedRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_srcrev_git_recipe_autorev_ok(self):
        """Test that AUTOREV in -git recipe passes."""
        from bake_linter.rules.patch import SrcrevUnpinnedRule
        
        content = '''SRCREV = "${AUTOREV}"
'''
        context = FileContext(
            path=Path("myapp-git.bb"),  # -git suffix indicates dev recipe
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SrcrevUnpinnedRule()
        results = rule.check(context)
        
        # Should not flag -git recipes
        assert len(results) == 0


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


class TestInstallRulesExtended:
    """Extended tests for install rules (INSTALL003-005)."""

    def test_mkdir_instead_of_install_d(self):
        """Test that mkdir -p in do_install is flagged."""
        from bake_linter.rules.install import MkdirInsteadOfInstallDRule
        
        content = '''do_install() {
    mkdir -p ${D}${bindir}
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MkdirInsteadOfInstallDRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "INSTALL003"

    def test_install_d_ok(self):
        """Test that install -d passes."""
        from bake_linter.rules.install import MkdirInsteadOfInstallDRule
        
        content = '''do_install() {
    install -d ${D}${bindir}
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MkdirInsteadOfInstallDRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_usr_local_installation(self):
        """Test that /usr/local installation is flagged."""
        from bake_linter.rules.install import UsrLocalInstallRule
        
        content = '''do_install() {
    install -m 0755 myapp ${D}/usr/local/bin/
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = UsrLocalInstallRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "INSTALL004"


class TestVariablesRules:
    """Tests for variables rules."""

    def test_git_recipe_without_srcpv(self):
        """Test that git recipe without SRCPV is flagged."""
        from bake_linter.rules.variables import GitRecipeWithoutSRCPVRule
        
        content = '''SRC_URI = "git://github.com/user/repo.git;protocol=https"
PV = "1.0"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = GitRecipeWithoutSRCPVRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "VARIABLES001"

    def test_git_recipe_with_srcpv_ok(self):
        """Test that git recipe with SRCPV passes."""
        from bake_linter.rules.variables import GitRecipeWithoutSRCPVRule
        
        content = '''SRC_URI = "git://github.com/user/repo.git;protocol=https"
PV = "1.0+git${SRCPV}"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = GitRecipeWithoutSRCPVRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_unconventional_s_workdir(self):
        """Test that S = ${WORKDIR} is flagged."""
        from bake_linter.rules.variables import UnconventionalSAssignmentRule
        
        content = '''S = "${WORKDIR}"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = UnconventionalSAssignmentRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "VARIABLES002"


class TestBbappendRulesExtended:
    """Extended tests for bbappend rules (BBAPPEND003-004)."""

    def test_version_specific_bbappend(self):
        """Test that version-specific bbappend is flagged."""
        from bake_linter.rules.bbappend import VersionSpecificBbappendRule
        
        content = '''FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
'''
        context = FileContext(
            path=Path("myrecipe_1.5.3.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = VersionSpecificBbappendRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "BBAPPEND003"

    def test_percent_bbappend_ok(self):
        """Test that %-wildcard bbappend passes."""
        from bake_linter.rules.bbappend import VersionSpecificBbappendRule
        
        content = '''FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
'''
        context = FileContext(
            path=Path("myrecipe_%.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = VersionSpecificBbappendRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_empty_bbappend(self):
        """Test that empty bbappend is flagged."""
        from bake_linter.rules.bbappend import EmptyBbappendRule
        
        content = '''# This is just a comment
# No actual content
'''
        context = FileContext(
            path=Path("myrecipe_%.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = EmptyBbappendRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "BBAPPEND004"


class TestDependencyRulesExtended:
    """Extended tests for dependency rules."""

    def test_missing_pkgconfig_inherit(self):
        """Test that pkg-config usage without inherit is flagged."""
        from bake_linter.rules.dependency import MissingPkgconfigInheritRule
        
        content = '''do_configure() {
    PKG_CONFIG_PATH="${STAGING_LIBDIR}/pkgconfig" oe_runconf
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MissingPkgconfigInheritRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "DEPENDENCY002"

    def test_with_pkgconfig_inherit_ok(self):
        """Test that pkg-config with inherit passes."""
        from bake_linter.rules.dependency import MissingPkgconfigInheritRule
        
        content = '''inherit pkgconfig autotools

do_configure() {
    oe_runconf
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MissingPkgconfigInheritRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_essential_in_rrecommends(self):
        """Test that essential library in RRECOMMENDS is flagged."""
        from bake_linter.rules.dependency import RrecommendsEssentialRule
        
        content = '''RRECOMMENDS:${PN} = "libssl"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = RrecommendsEssentialRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "DEPENDENCY003"


class TestSyntaxRules:
    """Tests for syntax rules."""

    def test_unmatched_quotes(self):
        """Test that unmatched quotes are flagged."""
        from bake_linter.rules.syntax import UnmatchedQuotesRule
        
        content = '''DESCRIPTION = "This is missing a quote
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = UnmatchedQuotesRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "SYNTAX001"

    def test_tabs_in_python(self):
        """Test that tabs in python functions are flagged."""
        from bake_linter.rules.syntax import TabsInPythonFunctionRule
        
        content = '''python do_custom() {
\tbb.note("Using tabs")
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = TabsInPythonFunctionRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "SYNTAX003"

    def test_unclosed_variable_expansion(self):
        """Test that unclosed ${} is flagged."""
        from bake_linter.rules.syntax import UnclosedVariableExpansionRule
        
        content = '''do_install() {
    install -m 0755 ${S/myapp ${D}${bindir}/
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = UnclosedVariableExpansionRule()
        results = rule.check(context)
        
        assert len(results) >= 1
        assert results[0].rule_id == "SYNTAX004"


class TestMetadataRules:
    """Tests for metadata rules."""

    def test_compatible_machine_syntax(self):
        """Test that COMPATIBLE_MACHINE without anchors is flagged."""
        from bake_linter.rules.metadata import CompatibleMachineSyntaxRule
        
        content = '''COMPATIBLE_MACHINE = "qemux86"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = CompatibleMachineSyntaxRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "METADATA002"

    def test_compatible_machine_with_anchors_ok(self):
        """Test that COMPATIBLE_MACHINE with anchors passes."""
        from bake_linter.rules.metadata import CompatibleMachineSyntaxRule
        
        content = '''COMPATIBLE_MACHINE = "^qemux86$"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = CompatibleMachineSyntaxRule()
        results = rule.check(context)
        
        assert len(results) == 0


class TestBestPracticeRules:
    """Tests for best practice rules."""

    def test_do_fetch_modification(self):
        """Test that do_fetch modification is flagged."""
        from bake_linter.rules.best_practices import DoFetchModificationRule
        
        content = '''do_fetch:append() {
    wget https://example.com/extra.tar.gz
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = DoFetchModificationRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "BESTPRACTICE001"

    def test_sed_in_do_install(self):
        """Test that sed -i in do_install is flagged."""
        from bake_linter.rules.best_practices import SedInDoInstallRule
        
        content = '''do_install() {
    sed -i 's/DEBUG/RELEASE/g' ${D}${bindir}/myapp
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SedInDoInstallRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "BESTPRACTICE004"


class TestSecurityRulesExtended:
    """Extended tests for security rules."""

    def test_dangerous_rm_rf(self):
        """Test that dangerous rm -rf is flagged."""
        from bake_linter.rules.security import DangerousRmRfRule
        
        content = '''do_install() {
    rm -rf ${D}${MY_VAR}/*
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = DangerousRmRfRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "SECURITY005"

    def test_eval_usage(self):
        """Test that eval usage is flagged."""
        from bake_linter.rules.security import EvalUsageRule
        
        content = '''do_configure() {
    eval ${CUSTOM_ARGS}
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = EvalUsageRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "SECURITY006"

    def test_build_path_leakage(self):
        """Test that build path leakage is flagged."""
        from bake_linter.rules.security import BuildPathLeakageRule
        
        content = '''do_install() {
    echo "DATA_DIR=${S}/data" > ${D}${sysconfdir}/myapp.conf
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = BuildPathLeakageRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "SECURITY007"


class TestCompatibilityRules:
    """Tests for compatibility rules."""

    def test_deprecated_compatible_host(self):
        """Test that COMPATIBLE_HOST without anchors is flagged."""
        from bake_linter.rules.compatibility import DeprecatedCompatibleHostRule
        
        content = '''COMPATIBLE_HOST = "i.86.*-linux"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = DeprecatedCompatibleHostRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "COMPAT001"

    def test_unjustified_machine_arch(self):
        """Test that MACHINE_ARCH without justification is flagged."""
        from bake_linter.rules.compatibility import UnjustifiedMachineArchRule
        
        content = '''PACKAGE_ARCH = "${MACHINE_ARCH}"
# Recipe just installs generic scripts
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = UnjustifiedMachineArchRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "COMPAT002"

    def test_machine_arch_with_kernel_module_ok(self):
        """Test that MACHINE_ARCH with kernel module passes."""
        from bake_linter.rules.compatibility import UnjustifiedMachineArchRule
        
        content = '''inherit module
PACKAGE_ARCH = "${MACHINE_ARCH}"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = UnjustifiedMachineArchRule()
        results = rule.check(context)
        
        assert len(results) == 0


class TestSyntaxRulesExtended:
    """Tests for extended syntax rules (SYNTAX005-006)."""

    def test_mixed_override_syntax_detected(self):
        """Test that mixing _append and :append is detected."""
        from bake_linter.rules.syntax import MixedOverrideSyntaxRule
        
        content = '''SRC_URI_append = " file://patch.patch"
CFLAGS:append = " -DFOO"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MixedOverrideSyntaxRule()
        results = rule.check(context)
        
        assert len(results) >= 1
        assert results[0].rule_id == "SYNTAX005"

    def test_single_override_syntax_ok(self):
        """Test that consistent syntax passes."""
        from bake_linter.rules.syntax import MixedOverrideSyntaxRule
        
        content = '''SRC_URI:append = " file://patch.patch"
CFLAGS:append = " -DFOO"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MixedOverrideSyntaxRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_invalid_override_ordering(self):
        """Test that :prepend after :append is flagged."""
        from bake_linter.rules.syntax import InvalidOverrideOrderingRule
        
        content = '''CFLAGS:append:prepend = " -DFOO"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = InvalidOverrideOrderingRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "SYNTAX006"


class TestPackageRules:
    """Tests for package configuration rules."""

    def test_rdepends_on_dev_package(self):
        """Test that RDEPENDS on -dev package is flagged."""
        from bake_linter.rules.package import RdependsOnDevPackageRule
        
        content = '''RDEPENDS:${PN} = "libfoo-dev"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = RdependsOnDevPackageRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "PKG001"
        assert "-dev" in results[0].message

    def test_rdepends_on_regular_package_ok(self):
        """Test that RDEPENDS on regular package passes."""
        from bake_linter.rules.package import RdependsOnDevPackageRule
        
        content = '''RDEPENDS:${PN} = "libfoo bash"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = RdependsOnDevPackageRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_files_not_matching_install(self):
        """Test that FILES paths not covered by install are flagged."""
        from bake_linter.rules.package import FilesNotMatchingInstallRule
        
        content = '''do_install() {
    install -d ${D}/opt/custom
    install -m 0755 mybin ${D}/opt/custom/mybin
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = FilesNotMatchingInstallRule()
        results = rule.check(context)
        
        assert len(results) >= 1
        assert results[0].rule_id == "PKG002"

    def test_wildcard_bbappend_overreach(self):
        """Test that wildcard bbappends with version-specific content are flagged."""
        from bake_linter.rules.package import WildcardBbappendOverreachRule
        
        content = '''SRCREV = "abc123def456"
SRC_URI += "file://fix-v2.0-build.patch"
'''
        context = FileContext(
            path=Path("myrecipe_%.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = WildcardBbappendOverreachRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "PKG003"


class TestSupplyChainRules:
    """Tests for supply chain and reproducibility rules."""

    def test_unpinned_branch_master(self):
        """Test that master branch usage is flagged."""
        from bake_linter.rules.supply_chain import UnpinnedBranchRule
        
        content = '''SRC_URI = "git://github.com/foo/bar.git;branch=master;protocol=https"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = UnpinnedBranchRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "REPRO001"
        assert "master" in results[0].message

    def test_stable_branch_ok(self):
        """Test that stable branch names pass."""
        from bake_linter.rules.supply_chain import UnpinnedBranchRule
        
        content = '''SRC_URI = "git://github.com/foo/bar.git;branch=stable-2.0;protocol=https"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = UnpinnedBranchRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_bbappend_src_uri_without_lic_check(self):
        """Test that bbappend modifying SRC_URI without license check is flagged."""
        from bake_linter.rules.supply_chain import MissingLicenseChecksumInBbappendRule
        
        content = '''SRC_URI += "file://custom-patch.patch"
'''
        context = FileContext(
            path=Path("test_%.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MissingLicenseChecksumInBbappendRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "SUPPLY001"

    def test_bbappend_with_lic_check_ok(self):
        """Test that bbappend with LIC_FILES_CHKSUM passes."""
        from bake_linter.rules.supply_chain import MissingLicenseChecksumInBbappendRule
        
        content = '''SRC_URI += "file://custom-patch.patch"
LIC_FILES_CHKSUM += "file://CUSTOM_LICENSE;md5=abc123"
'''
        context = FileContext(
            path=Path("test_%.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MissingLicenseChecksumInBbappendRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_unreliable_hosting_dropbox(self):
        """Test that Dropbox downloads are flagged."""
        from bake_linter.rules.supply_chain import UnreliableHostingRule
        
        content = '''SRC_URI = "https://www.dropbox.com/s/abc123/myfile.tar.gz"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = UnreliableHostingRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "SUPPLY002"


class TestTaskRules:
    """Tests for task implementation rules."""

    def test_unquoted_variable_d(self):
        """Test that unquoted ${D} is flagged."""
        from bake_linter.rules.task import UnquotedVariableRule
        
        content = '''do_install() {
    rm -rf ${D}${libdir}/*
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = UnquotedVariableRule()
        results = rule.check(context)
        
        # Should flag D as unquoted
        assert any(r.rule_id == "TASK001" for r in results)

    def test_sudo_in_task(self):
        """Test that sudo usage is flagged."""
        from bake_linter.rules.task import SudoUsageRule
        
        content = '''do_install() {
    sudo mkdir -p /opt/myapp
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SudoUsageRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "TASK002"
        assert results[0].severity == Severity.ERROR

    def test_network_in_compile(self):
        """Test that network access in do_compile is flagged."""
        from bake_linter.rules.task import NetworkAccessInCompileRule
        
        content = '''do_compile() {
    npm install
    make all
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = NetworkAccessInCompileRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "TASK003"

    def test_network_in_fetch_ok(self):
        """Test that network access in do_fetch is allowed."""
        from bake_linter.rules.task import NetworkAccessInCompileRule
        
        content = '''do_fetch() {
    wget http://example.com/file.tar.gz
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = NetworkAccessInCompileRule()
        results = rule.check(context)
        
        # do_fetch is not in BUILD_TASKS, so should not trigger
        assert len(results) == 0


class TestPythonCodeRules:
    """Tests for Python code rules."""

    def test_print_in_python_function(self):
        """Test that print() in Python function is flagged."""
        from bake_linter.rules.python_code import PrintVsBbNoteRule
        
        content = '''python __anonymous() {
    print("Debug message")
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = PrintVsBbNoteRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "PYTHON001"

    def test_bb_note_ok(self):
        """Test that bb.note() passes."""
        from bake_linter.rules.python_code import PrintVsBbNoteRule
        
        content = '''python __anonymous() {
    bb.note("Debug message")
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = PrintVsBbNoteRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_direct_var_assignment(self):
        """Test that direct BitBake var assignment is flagged."""
        from bake_linter.rules.python_code import DirectVarAssignmentRule
        
        content = '''python __anonymous() {
    PN = "mypackage"
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = DirectVarAssignmentRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "PYTHON002"

    def test_d_setvar_ok(self):
        """Test that d.setVar() passes."""
        from bake_linter.rules.python_code import DirectVarAssignmentRule
        
        content = '''python __anonymous() {
    d.setVar('PN', 'mypackage')
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = DirectVarAssignmentRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_sys_exit_in_anonymous(self):
        """Test that sys.exit() in anonymous Python is flagged."""
        from bake_linter.rules.python_code import AnonymousPythonIssuesRule
        
        content = '''python __anonymous() {
    if error:
        sys.exit(1)
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = AnonymousPythonIssuesRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "PYTHON003"


class TestPortabilityRules:
    """Tests for portability rules."""

    def test_hardcoded_march(self):
        """Test that hardcoded -march is flagged."""
        from bake_linter.rules.portability import HardcodedCpuFlagsRule
        
        content = '''CFLAGS += "-march=x86-64"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = HardcodedCpuFlagsRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "PORT001"

    def test_absolute_usr_lib_path(self):
        """Test that /usr/lib is flagged."""
        from bake_linter.rules.portability import AbsoluteHostPathRule
        
        content = '''do_configure() {
    ./configure --libdir=/usr/lib
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = AbsoluteHostPathRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "PORT002"
        assert results[0].severity == Severity.ERROR

    def test_yocto_variable_path_ok(self):
        """Test that ${D}${libdir} passes."""
        from bake_linter.rules.portability import AbsoluteHostPathRule
        
        content = '''do_install() {
    install -d ${D}${libdir}
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = AbsoluteHostPathRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_non_portable_sed(self):
        """Test that GNU-specific sed is flagged."""
        from bake_linter.rules.portability import NonPortableSedRule
        
        content = '''do_configure() {
    sed -r 's/foo/bar/' file.txt
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = NonPortableSedRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "PORT003"


class TestDocumentationRules:
    """Tests for documentation rules."""

    def test_identical_summary_description(self):
        """Test that identical SUMMARY and DESCRIPTION is flagged."""
        from bake_linter.rules.documentation import IdenticalSummaryDescriptionRule
        
        content = '''SUMMARY = "My package"
DESCRIPTION = "My package"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = IdenticalSummaryDescriptionRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "DOC001"

    def test_different_summary_description_ok(self):
        """Test that different SUMMARY and DESCRIPTION passes."""
        from bake_linter.rules.documentation import IdenticalSummaryDescriptionRule
        
        content = '''SUMMARY = "My package"
DESCRIPTION = "My package provides X, Y, and Z features for..."
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = IdenticalSummaryDescriptionRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_missing_summary(self):
        """Test that missing SUMMARY is flagged."""
        from bake_linter.rules.documentation import MissingSummaryRule
        
        content = '''LICENSE = "MIT"
DESCRIPTION = "My package provides..."
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MissingSummaryRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "DOC002"

    def test_truncated_description(self):
        """Test that short DESCRIPTION is flagged."""
        from bake_linter.rules.documentation import TruncatedDescriptionRule
        
        content = '''DESCRIPTION = "A package"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = TruncatedDescriptionRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "DOC003"
