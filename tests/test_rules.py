# -*- coding: utf-8 -*-
"""
Unit tests for lint rules.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

import pytest
from pathlib import Path
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext, VariableAssignment
from bake_linter.core.registry import RuleRegistry, get_registry
from bake_linter.rules.license import LicenseRequiredRule, LicenseTypoRule, LicFilesChkSumRule
from bake_linter.rules.mandatory import SummaryDescriptionRule, SrcUriRule, InheritCheck
from bake_linter.rules.deprecated import DeprecatedOverrideSyntaxRule
from bake_linter.rules.naming import RecipeNamingRule, VariableNamingRule
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

    def test_native_recipe_without_version_not_flagged(self):
        """Test that native recipes without version in filename are NOT flagged.
        
        Native recipes commonly use PV in the recipe content and don't
        require version in the filename.
        """
        content = '''SUMMARY = "Rockchip binary tools"
LICENSE = "CLOSED"
PV = "1.0+git${SRCPV}"
SRCREV = "abc123..."
'''
        context = FileContext(
            path=Path("rk-binary-native.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = RecipeNamingRule()
        results = rule.check(context)
        
        # Should NOT flag - native recipe with PV defined
        version_issues = [r for r in results if "version" in r.message.lower()]
        assert len(version_issues) == 0

    def test_packagegroup_without_version_not_flagged(self):
        """Test that packagegroup recipes without version are NOT flagged."""
        content = '''SUMMARY = "Core packagegroup"
LICENSE = "MIT"
inherit packagegroup
RDEPENDS:${PN} = "base-files"
'''
        context = FileContext(
            path=Path("packagegroup-core.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = RecipeNamingRule()
        results = rule.check(context)
        
        # Should NOT flag - packagegroups don't need version
        version_issues = [r for r in results if "version" in r.message.lower()]
        assert len(version_issues) == 0

    def test_cross_recipe_without_version_not_flagged(self):
        """Test that cross-compiler recipes without version are NOT flagged."""
        content = '''SUMMARY = "GCC cross compiler"
LICENSE = "GPL-3.0"
PV = "13.2"
'''
        context = FileContext(
            path=Path("gcc-cross.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = RecipeNamingRule()
        results = rule.check(context)
        
        # Should NOT flag - cross recipes don't need version in filename
        version_issues = [r for r in results if "version" in r.message.lower()]
        assert len(version_issues) == 0

    def test_recipe_with_pv_in_content_not_flagged(self):
        """Test that recipe with PV defined is NOT flagged for missing version."""
        content = '''SUMMARY = "Some tool"
LICENSE = "MIT"
PV = "2.0"
'''
        context = FileContext(
            path=Path("sometool.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = RecipeNamingRule()
        results = rule.check(context)
        
        # Should NOT flag - PV is defined in recipe
        version_issues = [r for r in results if "version" in r.message.lower()]
        assert len(version_issues) == 0

    def test_lowercase_bitbake_variable_flagged(self):
        """Test that lowercase BitBake metadata variables are flagged."""
        content = '''SUMMARY = "Test"
my_custom_var = "value"
LICENSE = "MIT"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(),
            variables={},
        )
        
        rule = VariableNamingRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "NAMING001"
        assert "my_custom_var" in results[0].message

    def test_lowercase_python_variable_not_flagged(self):
        """Test that Python local variables inside python functions are NOT flagged.
        
        Python functions follow PEP 8 style (lowercase_with_underscores for local vars).
        This is correct style, NOT a BitBake naming violation.
        """
        content = '''SUMMARY = "Test"
python build_syslinux_cfg:append () {
    try:
        menu_default = d.getVar('SYSLINUX_DEFAULT_MENU_FOR_HDDIMG_INSTALL')
        if menu_default:
            with open(cfile, 'a') as cfgadd:
                cfgadd.write(menu_default + '\\n')
    except Exception as e:
        bb.error(str(e))
}
LICENSE = "MIT"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(),
            variables={},
        )
        
        rule = VariableNamingRule()
        results = rule.check(context)
        
        # Should NOT flag menu_default - it's a Python local variable
        assert not any("menu_default" in r.message for r in results)
        assert len(results) == 0

    def test_lowercase_shell_variable_not_flagged(self):
        """Test that shell variables inside do_* functions are NOT flagged.
        
        Shell functions may use lowercase variables which is valid shell style.
        """
        content = '''SUMMARY = "Test"
do_install:append() {
    local_var="/usr/local/bin"
    install -d ${D}${local_var}
}
LICENSE = "MIT"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(),
            variables={},
        )
        
        rule = VariableNamingRule()
        results = rule.check(context)
        
        # Should NOT flag local_var - it's inside a shell function
        assert not any("local_var" in r.message for r in results)
        assert len(results) == 0

    def test_python_anonymous_function_not_flagged(self):
        """Test that Python variables in anonymous functions are NOT flagged."""
        content = '''SUMMARY = "Test"
python __anonymous() {
    pn = d.getVar('PN')
    depends = d.getVar('DEPENDS') or ''
    d.setVar('DEPENDS', depends + ' ' + pn + '-native')
}
LICENSE = "MIT"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(),
            variables={},
        )
        
        rule = VariableNamingRule()
        results = rule.check(context)
        
        # Should NOT flag pn, depends - they're Python local variables
        assert len(results) == 0

    def test_lowercase_custom_shell_function_not_flagged(self):
        """Test that shell variables inside custom shell functions are NOT flagged.
        
        Custom shell functions like uboot_compile_config() should not have their
        local variables flagged - lowercase is standard shell convention.
        """
        content = '''UBOOT_BINARY = "u-boot.img"
uboot_compile_config () {
    i=$1
    config=$2
    type=$3
    oe_runmake -C ${S} O=${B}/${config} ${UBOOT_MAKE_TARGET}
    unset k
    for binary in ${UBOOT_BINARIES}; do
        k=$(expr $k + 1);
        if [ $k -eq $i ]; then
            echo "Found"
        fi
    done
}
LICENSE = "MIT"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(),
            variables={},
        )
        
        rule = VariableNamingRule()
        results = rule.check(context)
        
        # Should NOT flag i, config, type, k - they're shell function local variables
        assert not any("'i'" in r.message for r in results)
        assert not any("config" in r.message for r in results)
        assert not any("type" in r.message for r in results)
        assert not any("'k'" in r.message for r in results)
        assert len(results) == 0

    def test_hostname_lowercase_exception_not_flagged(self):
        """Test that 'hostname' is NOT flagged - it's a known Yocto lowercase variable.
        
        The hostname variable is used by base-files recipe to control /etc/hostname.
        Setting it to empty string prevents /etc/hostname creation.
        """
        content = '''COMPATIBLE_MACHINE = "^(max)$"
# set hostname to "" so /etc/hostname is not created
hostname = ""
SRC_URI += "file://config"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(),
            variables={},
        )
        
        rule = VariableNamingRule()
        results = rule.check(context)
        
        # Should NOT flag hostname - it's a known Yocto lowercase exception
        assert not any("hostname" in r.message for r in results)
        assert len(results) == 0


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

    def test_hardcoded_path_in_code_flagged(self):
        """Test that hardcoded paths in actual code are flagged."""
        from bake_linter.rules.style import HardcodedPathsRule
        
        content = '''do_install() {
    install -d ${D}/etc/myapp
    install -m 0644 ${WORKDIR}/config ${D}/etc/myapp/
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = HardcodedPathsRule()
        results = rule.check(context)
        
        # Should flag hardcoded /etc paths in code
        assert any(r.rule_id == "STYLE003" for r in results)
        assert any("sysconfdir" in r.message for r in results)

    def test_hardcoded_path_in_summary_not_flagged(self):
        """Test that hardcoded paths in SUMMARY are NOT flagged.
        
        Documentation variables should use literal paths for human readability.
        Users reading package descriptions need to see /etc/hosts, not ${sysconfdir}/hosts.
        """
        from bake_linter.rules.style import HardcodedPathsRule
        
        content = '''SUMMARY = "Update /etc/hosts with entries from /etc/hosts.d"
LICENSE = "CLOSED"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = HardcodedPathsRule()
        results = rule.check(context)
        
        # Should NOT flag /etc in SUMMARY - it's documentation
        assert len(results) == 0

    def test_hardcoded_path_in_description_not_flagged(self):
        """Test that hardcoded paths in DESCRIPTION are NOT flagged."""
        from bake_linter.rules.style import HardcodedPathsRule
        
        content = '''DESCRIPTION = "This tool reads configuration from /etc/myapp.conf and writes logs to /var/log/myapp.log"
LICENSE = "MIT"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = HardcodedPathsRule()
        results = rule.check(context)
        
        # Should NOT flag /etc or /var in DESCRIPTION - it's documentation
        assert len(results) == 0

    def test_hardcoded_path_hint_contains_suggestion(self):
        """Test that hardcoded path warnings include helpful variable suggestions."""
        from bake_linter.rules.style import HardcodedPathsRule
        
        content = '''do_install() {
    install -d ${D}/usr/share/myapp
    install -d ${D}/usr/bin
    install -d ${D}/var/lib/myapp
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = HardcodedPathsRule()
        results = rule.check(context)
        
        # Should have 3 warnings with proper suggestions
        assert len(results) == 3
        
        # Check that hints contain the variable suggestions
        datadir_result = [r for r in results if 'datadir' in r.message][0]
        assert '${datadir}' in datadir_result.hint
        
        bindir_result = [r for r in results if 'bindir' in r.message][0]
        assert '${bindir}' in bindir_result.hint
        
        sharedstatedir_result = [r for r in results if 'sharedstatedir' in r.message][0]
        assert '${sharedstatedir}' in sharedstatedir_result.hint

    def test_hardcoded_path_shebang_not_flagged(self):
        """Test that shebang patterns like #!/usr/bin/env are NOT flagged.
        
        Shebangs are standard Unix runtime conventions, not build-time paths.
        The pattern #!/usr/bin/env python3 is the portable way to find Python.
        """
        from bake_linter.rules.style import HardcodedPathsRule
        
        content = '''do_patch:append() {
    for s in grep -rIl python ${S}/scripts; do
        sed -i -e '1s|^#!.*python[23]*|#!/usr/bin/env ${PYTHON_PN}|' $s
    done
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = HardcodedPathsRule()
        results = rule.check(context)
        
        # Should NOT flag #!/usr/bin/env - it's a shebang pattern
        assert len(results) == 0

    def test_hardcoded_path_various_shebangs_not_flagged(self):
        """Test that various shebang patterns are NOT flagged."""
        from bake_linter.rules.style import HardcodedPathsRule
        
        content = '''do_install:append() {
    # Create wrapper with shebang
    cat > ${D}${bindir}/wrapper << 'EOF'
#!/bin/sh
exec myprogram "$@"
EOF
    
    # Fix shebang in Python scripts
    sed -i '1s|.*|#!/usr/bin/env python3|' ${D}${bindir}/script.py
    
    # Another shebang pattern
    echo '#!/bin/bash' > ${D}${bindir}/test.sh
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = HardcodedPathsRule()
        results = rule.check(context)
        
        # Should NOT flag any shebangs - they are runtime conventions
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

    def test_hardcoded_systemd_path_in_files_flagged(self):
        """Test that hardcoded systemd paths in FILES are flagged with INFO level."""
        from bake_linter.rules.style import HardcodedSystemdPathInFilesRule
        
        content = '''FILES:${PN} += "\\
    /usr/lib/systemd/system/max-ps-ssh-tunnel-restart.path \\
    /usr/lib/systemd/system/multi-user.target.wants/max-ps-ssh-tunnel-restart.path \\
    /usr/lib/systemd/system/max-ps-ssh-tunnel-restart.service \\
    /usr/lib/systemd/system/max-ps-ssh-tunnel.service \\
    /usr/lib/systemd/system/sshd.socket.d/sshd-listen-localhost.conf \\
"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = HardcodedSystemdPathInFilesRule()
        results = rule.check(context)
        
        # Should flag with INFO severity (style concern, not error)
        assert len(results) == 5
        assert all(r.rule_id == "STYLE011" for r in results)
        assert all(r.severity == Severity.INFO for r in results)
        assert all("${systemd_system_unitdir}" in r.hint for r in results)

    def test_hardcoded_systemd_path_in_files_single_line(self):
        """Test single-line FILES with systemd path is flagged by STYLE011."""
        from bake_linter.rules.style import HardcodedSystemdPathInFilesRule
        
        content = '''FILES:${PN} += "/usr/lib/systemd/system/*.service"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = HardcodedSystemdPathInFilesRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "STYLE011"
        assert results[0].severity == Severity.INFO
        assert "consistency" in results[0].hint.lower()

    def test_files_with_systemd_variable_not_flagged(self):
        """Test that FILES with proper systemd variables is NOT flagged."""
        from bake_linter.rules.style import HardcodedSystemdPathInFilesRule
        
        content = '''FILES:${PN} += "\\
    ${systemd_system_unitdir}/my-service.service \\
    ${systemd_system_unitdir}/multi-user.target.wants/my-service.service \\
"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = HardcodedSystemdPathInFilesRule()
        results = rule.check(context)
        
        # Using proper variables - no issues
        assert len(results) == 0

    def test_variable_assignment_no_spaces_flagged(self):
        """Test that variable assignments without spaces are flagged."""
        from bake_linter.rules.style import VariableAssignmentSpacingRule
        
        content = '''FOO="bar"
MY_VAR+="value"
ANOTHER:=test
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = VariableAssignmentSpacingRule()
        results = rule.check(context)
        
        # All three should be flagged for missing spaces
        assert len(results) == 3
        assert all(r.rule_id == "STYLE012" for r in results)
        assert all("space" in r.message.lower() for r in results)

    def test_variable_assignment_proper_spacing_ok(self):
        """Test that properly spaced variable assignments pass."""
        from bake_linter.rules.style import VariableAssignmentSpacingRule
        
        content = '''FOO = "bar"
MY_VAR += "value"
ANOTHER := "test"
OPTIONAL ?= "maybe"
WEAK ??= "default"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = VariableAssignmentSpacingRule()
        results = rule.check(context)
        
        # All have proper spacing
        assert len(results) == 0

    def test_variable_assignment_spacing_skips_functions(self):
        """Test that variable assignment rule skips shell/Python functions."""
        from bake_linter.rules.style import VariableAssignmentSpacingRule
        
        content = '''FOO = "bar"

do_install() {
    VAR="value"
    ANOTHER="test"
}

python do_configure() {
    VAR="value"
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = VariableAssignmentSpacingRule()
        results = rule.check(context)
        
        # Should not flag variables inside functions
        assert len(results) == 0

    def test_variable_assignment_missing_space_before_only(self):
        """Test that missing space before operator is flagged."""
        from bake_linter.rules.style import VariableAssignmentSpacingRule
        
        content = '''FOO= "bar"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = VariableAssignmentSpacingRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert "before" in results[0].message.lower()

    def test_variable_assignment_missing_space_after_only(self):
        """Test that missing space after operator is flagged."""
        from bake_linter.rules.style import VariableAssignmentSpacingRule
        
        content = '''FOO ="bar"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = VariableAssignmentSpacingRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert "after" in results[0].message.lower()

    def test_single_quote_in_assignment_flagged(self):
        """Test that single quotes in variable assignments are flagged."""
        from bake_linter.rules.style import SingleQuoteUsageRule
        
        content = '''FOO = 'bar'
MY_VAR = 'some value'
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SingleQuoteUsageRule()
        results = rule.check(context)
        
        # Both should be flagged
        assert len(results) == 2
        assert all(r.rule_id == "STYLE013" for r in results)
        assert all("single quote" in r.message.lower() for r in results)

    def test_double_quote_in_assignment_ok(self):
        """Test that double quotes in variable assignments pass."""
        from bake_linter.rules.style import SingleQuoteUsageRule
        
        content = '''FOO = "bar"
MY_VAR = "some value"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SingleQuoteUsageRule()
        results = rule.check(context)
        
        # Double quotes are correct
        assert len(results) == 0

    def test_single_quote_skips_shell_functions(self):
        """Test that single quotes inside shell functions are not flagged."""
        from bake_linter.rules.style import SingleQuoteUsageRule
        
        content = '''FOO = "bar"

do_install() {
    echo 'Hello'
    MY_VAR='test'
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SingleQuoteUsageRule()
        results = rule.check(context)
        
        # Should not flag quotes inside functions
        assert len(results) == 0

    def test_tab_in_variable_definition_flagged(self):
        """Test that tabs in variable definitions are flagged."""
        from bake_linter.rules.style import TabInVariableDefinitionRule
        
        content = '''FOO = "value \\
\tcontinuation"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = TabInVariableDefinitionRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "STYLE014"
        assert "tab" in results[0].message.lower()

    def test_tab_in_variable_single_line_flagged(self):
        """Test that tabs in single-line variable definitions are flagged."""
        from bake_linter.rules.style import TabInVariableDefinitionRule
        
        content = '''FOO = "value\twith tab"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = TabInVariableDefinitionRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "STYLE014"

    def test_spaces_in_variable_definition_ok(self):
        """Test that spaces in variable definitions pass."""
        from bake_linter.rules.style import TabInVariableDefinitionRule
        
        content = '''FOO = "value \\
    continuation"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = TabInVariableDefinitionRule()
        results = rule.check(context)
        
        # No tabs, should pass
        assert len(results) == 0

    def test_tab_skips_shell_functions(self):
        """Test that tabs inside shell functions are not flagged."""
        from bake_linter.rules.style import TabInVariableDefinitionRule
        
        content = '''FOO = "bar"

do_install() {
\techo "Hello"
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = TabInVariableDefinitionRule()
        results = rule.check(context)
        
        # Should not flag tabs inside functions
        assert len(results) == 0

    def test_multiline_inconsistent_indentation_flagged(self):
        """Test that inconsistent continuation indentation is flagged."""
        from bake_linter.rules.style import MultilineContinuationAlignmentRule
        
        content = '''FOO = "value \\
    continuation1 \\
  continuation2 \\
"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MultilineContinuationAlignmentRule()
        results = rule.check(context)
        
        # Third line has different indentation
        assert len(results) >= 1
        assert results[0].rule_id == "STYLE015"
        assert "inconsistent" in results[0].message.lower()

    def test_multiline_consistent_indentation_ok(self):
        """Test that consistent continuation indentation passes."""
        from bake_linter.rules.style import MultilineContinuationAlignmentRule
        
        content = '''FOO = "value \\
    continuation1 \\
    continuation2 \\
"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MultilineContinuationAlignmentRule()
        results = rule.check(context)
        
        # Consistent indentation
        assert len(results) == 0

    def test_multiline_insufficient_indentation_flagged(self):
        """Test that insufficient continuation indentation is flagged."""
        from bake_linter.rules.style import MultilineContinuationAlignmentRule
        
        content = '''FOO = "value \\
  x \\
"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MultilineContinuationAlignmentRule()
        results = rule.check(context)
        
        # Only 2 spaces indentation, should be flagged
        assert len(results) >= 1
        assert "insufficient" in results[0].message.lower() or "indentation" in results[0].message.lower()

    def test_multiline_skips_shell_functions(self):
        """Test that multiline rule skips shell functions."""
        from bake_linter.rules.style import MultilineContinuationAlignmentRule
        
        content = '''do_install() {
    FOO="value \\
  continuation"
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MultilineContinuationAlignmentRule()
        results = rule.check(context)
        
        # Should not flag inside functions
        assert len(results) == 0

    def test_src_uri_multiline_proper_format(self):
        """Test that SRC_URI with proper multiline format passes."""
        from bake_linter.rules.style import MultilineContinuationAlignmentRule
        
        content = '''SRC_URI = "\\
    file://patch1.patch \\
    file://patch2.patch \\
"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MultilineContinuationAlignmentRule()
        results = rule.check(context)
        
        # Proper SRC_URI format
        assert len(results) == 0

    def test_python_function_tabs_flagged(self):
        """Test that tabs in Python functions are flagged."""
        from bake_linter.rules.style import PythonFunctionIndentationRule
        
        content = '''python do_configure() {
\tbb.note("Hello")
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = PythonFunctionIndentationRule()
        results = rule.check(context)
        
        assert len(results) >= 1
        assert results[0].rule_id == "STYLE016"
        assert "tab" in results[0].message.lower()

    def test_python_function_4_spaces_ok(self):
        """Test that 4-space indentation in Python functions passes."""
        from bake_linter.rules.style import PythonFunctionIndentationRule
        
        content = '''python do_configure() {
    bb.note("Hello")
    if True:
        bb.note("Nested")
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = PythonFunctionIndentationRule()
        results = rule.check(context)
        
        # 4-space indentation is correct
        assert len(results) == 0

    def test_python_function_wrong_indent_flagged(self):
        """Test that non-4-space indentation in Python functions is flagged."""
        from bake_linter.rules.style import PythonFunctionIndentationRule
        
        content = '''python do_configure() {
   bb.note("Hello")
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = PythonFunctionIndentationRule()
        results = rule.check(context)
        
        # 3-space indentation should be flagged
        assert len(results) >= 1
        assert "not multiple of 4" in results[0].message.lower() or "indentation" in results[0].message.lower()

    def test_anonymous_python_function_checked(self):
        """Test that anonymous Python functions are also checked."""
        from bake_linter.rules.style import PythonFunctionIndentationRule
        
        content = '''python () {
\tbb.note("Anonymous")
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = PythonFunctionIndentationRule()
        results = rule.check(context)
        
        assert len(results) >= 1
        assert results[0].rule_id == "STYLE016"

    def test_recipe_variable_order_correct(self):
        """Test that properly ordered variables pass."""
        from bake_linter.rules.style import RecipeVariableOrderRule
        
        content = '''SUMMARY = "Test recipe"
DESCRIPTION = "A test recipe"
HOMEPAGE = "https://example.com"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=xxx"
DEPENDS = "foo"
SRC_URI = "https://example.com/file.tar.gz"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = RecipeVariableOrderRule()
        results = rule.check(context)
        
        # Properly ordered
        assert len(results) == 0

    def test_recipe_variable_order_wrong_flagged(self):
        """Test that incorrectly ordered variables are flagged."""
        from bake_linter.rules.style import RecipeVariableOrderRule
        
        content = '''LICENSE = "MIT"
SUMMARY = "Test recipe"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = RecipeVariableOrderRule()
        results = rule.check(context)
        
        # SUMMARY should come before LICENSE - but this is a minor diff (priority 1 vs 11)
        # The rule flags significant differences (>= 10 priority points)
        assert len(results) >= 1

    def test_license_order_wrong_flagged(self):
        """Test that LIC_FILES_CHKSUM before LICENSE is flagged."""
        from bake_linter.rules.style import LicenseVariablesOrderRule
        
        content = '''LIC_FILES_CHKSUM = "file://LICENSE;md5=xxx"
LICENSE = "MIT"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = LicenseVariablesOrderRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "STYLE018"
        assert "before LICENSE" in results[0].message

    def test_license_order_correct_ok(self):
        """Test that LICENSE before LIC_FILES_CHKSUM passes."""
        from bake_linter.rules.style import LicenseVariablesOrderRule
        
        content = '''LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=xxx"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = LicenseVariablesOrderRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_source_variables_order_wrong_flagged(self):
        """Test that SRCREV before SRC_URI is flagged."""
        from bake_linter.rules.style import SourceVariablesOrderRule
        
        content = '''SRCREV = "abc123"
SRC_URI = "git://github.com/test/repo.git"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SourceVariablesOrderRule()
        results = rule.check(context)
        
        assert len(results) >= 1
        assert results[0].rule_id == "STYLE019"
        assert "before SRC_URI" in results[0].message

    def test_source_variables_order_correct_ok(self):
        """Test that SRC_URI → SRCREV → S order passes."""
        from bake_linter.rules.style import SourceVariablesOrderRule
        
        content = '''SRC_URI = "git://github.com/test/repo.git"
SRCREV = "abc123"
S = "${WORKDIR}/git"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SourceVariablesOrderRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_metadata_before_license_wrong_flagged(self):
        """Test that metadata after LICENSE is flagged."""
        from bake_linter.rules.style import MetadataBeforeLicenseRule
        
        content = '''LICENSE = "MIT"
SUMMARY = "Test recipe"
HOMEPAGE = "https://example.com"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MetadataBeforeLicenseRule()
        results = rule.check(context)
        
        # SUMMARY and HOMEPAGE after LICENSE should be flagged
        assert len(results) >= 2
        assert all(r.rule_id == "STYLE020" for r in results)

    def test_metadata_before_license_correct_ok(self):
        """Test that metadata before LICENSE passes."""
        from bake_linter.rules.style import MetadataBeforeLicenseRule
        
        content = '''SUMMARY = "Test recipe"
HOMEPAGE = "https://example.com"
LICENSE = "MIT"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MetadataBeforeLicenseRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_task_order_wrong_flagged(self):
        """Test that tasks in wrong order are flagged."""
        from bake_linter.rules.style import TaskOrderRule
        
        content = '''do_install() {
    echo "install"
}

do_configure() {
    echo "configure"
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = TaskOrderRule()
        results = rule.check(context)
        
        # do_install before do_configure is wrong
        assert len(results) >= 1
        assert results[0].rule_id == "STYLE021"

    def test_task_order_correct_ok(self):
        """Test that tasks in correct order pass."""
        from bake_linter.rules.style import TaskOrderRule
        
        content = '''do_configure() {
    echo "configure"
}

do_compile() {
    echo "compile"
}

do_install() {
    echo "install"
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = TaskOrderRule()
        results = rule.check(context)
        
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

    def test_git_uri_with_explicit_secure_protocol_is_not_flagged(self):
        """``git://`` is the bitbake fetcher scheme, not the wire protocol: the
        transport comes from ``;protocol=`` (fetch2/git.py urldata_init). Poky
        writes git://...;protocol=https 973 times, so the scheme alone is not a
        finding."""
        lines = [
            'SRC_URI = "git://github.com/user/repo.git;protocol=https;branch=main"\n',
            'SRC_URI += "git://git.example.com/org/thing.git;protocol=ssh;branch=master"\n',
            'SRC_URI += "gitsm://example.com/sub.git;protocol=https;branch=main"\n',
        ]
        context = FileContext(
            path=Path("test_1.0.bb"),
            content="".join(lines),
            lines=lines,
            variables={},
        )

        rule = InsecureUriRule()
        results = rule.check(context)

        assert results == []

    def test_git_uri_with_plaintext_protocol_is_flagged(self):
        """An explicit plaintext protocol is still a finding."""
        lines = ['SRC_URI = "git://example.com/repo.git;protocol=git;branch=main"\n']
        context = FileContext(
            path=Path("test_1.0.bb"),
            content="".join(lines),
            lines=lines,
            variables={},
        )

        rule = InsecureUriRule()
        results = rule.check(context)

        assert len(results) == 1
        assert results[0].rule_id == "SECURITY001"


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

    def test_systemd_bbappend_not_flagged(self):
        """Test that .bbappend files using systemd are NOT flagged.
        
        .bbappend files inherit from their base recipe, so they don't
        need to explicitly add 'inherit systemd'.
        """
        from bake_linter.rules.systemd import SystemdWithoutInheritRule
        
        content = '''FILESEXTRAPATHS:prepend:fusion := "${THISDIR}/files:"
SRC_URI:append = " \\
    file://99-no-restrictsuid.conf \\
    "
do_install:append:fusion() {
    install -d ${D}${systemd_system_unitdir}
    install -d ${D}${systemd_system_unitdir}/data-defaults.service.d
    install -m 644 ${WORKDIR}/99-no-restrictsuid.conf ${D}${systemd_system_unitdir}/data-defaults.service.d
}
'''
        context = FileContext(
            path=Path("systemd_%.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdWithoutInheritRule()
        results = rule.check(context)
        
        # .bbappend files inherit from base recipe - should NOT be flagged
        assert len(results) == 0

    def test_systemd_inc_file_not_flagged(self):
        """Test that .inc files using systemd are NOT flagged.
        
        .inc files are included by recipes that handle the inherit.
        """
        from bake_linter.rules.systemd import SystemdWithoutInheritRule
        
        content = '''do_install() {
    install -d ${D}${systemd_system_unitdir}
    install -m 644 ${WORKDIR}/foo.service ${D}${systemd_system_unitdir}/
}
'''
        context = FileContext(
            path=Path("systemd-common.inc"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdWithoutInheritRule()
        results = rule.check(context)
        
        # .inc files are included by others - should NOT be flagged
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

    def test_systemd_src_uri_path_not_flagged(self):
        """Test that systemd paths in SRC_URI are NOT flagged (source location)."""
        from bake_linter.rules.systemd import SystemdHardcodedPathsRule
        
        content = '''SRC_URI = "git://github.com/example/repo.git;protocol=https;branch=main \\
           file://0001-fix.patch \\
           file://res/usr/lib/systemd/system/myservice.service \\
           file://res/usr/bin/myscript \\
           "
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdHardcodedPathsRule()
        results = rule.check(context)
        
        # SRC_URI paths are source file locations - should NOT be flagged
        assert len(results) == 0

    def test_systemd_workdir_source_with_proper_dest_not_flagged(self):
        """Test that source path from WORKDIR with proper dest is NOT flagged."""
        from bake_linter.rules.systemd import SystemdHardcodedPathsRule
        
        content = '''do_install() {
    install -d ${D}${systemd_system_unitdir}
    install -m 644 ${WORKDIR}/res/usr/lib/systemd/system/myservice.service ${D}${systemd_system_unitdir}
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
        
        # Source path from ${WORKDIR} with proper ${D}${systemd_system_unitdir} dest
        # should NOT be flagged
        assert len(results) == 0

    def test_systemd_hardcoded_dest_flagged(self):
        """Test that hardcoded DESTINATION paths ARE flagged."""
        from bake_linter.rules.systemd import SystemdHardcodedPathsRule
        
        content = '''do_install() {
    install -d ${D}/usr/lib/systemd/system
    install -m 644 myservice.service ${D}/usr/lib/systemd/system/
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
        
        # Hardcoded destination paths should BE flagged
        assert len(results) >= 1
        assert all(r.rule_id == "SYSTEMD003" for r in results)

    def test_systemd_files_variable_not_flagged(self):
        """Test that hardcoded systemd paths in FILES are NOT flagged by SYSTEMD003.
        
        FILES paths are style concerns (STYLE011), not errors.
        """
        from bake_linter.rules.systemd import SystemdHardcodedPathsRule
        
        content = '''FILES:${PN} += "\\
    /usr/lib/systemd/system/max-ps-ssh-tunnel-restart.path \\
    /usr/lib/systemd/system/multi-user.target.wants/max-ps-ssh-tunnel-restart.path \\
    /usr/lib/systemd/system/max-ps-ssh-tunnel-restart.service \\
    /usr/lib/systemd/system/max-ps-ssh-tunnel.service \\
    /usr/lib/systemd/system/sshd.socket.d/sshd-listen-localhost.conf \\
"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdHardcodedPathsRule()
        results = rule.check(context)
        
        # FILES paths should NOT be flagged by SYSTEMD003 (handled by STYLE011)
        assert len(results) == 0

    def test_systemd_files_single_line_not_flagged(self):
        """Test that single-line FILES with systemd path is NOT flagged by SYSTEMD003."""
        from bake_linter.rules.systemd import SystemdHardcodedPathsRule
        
        content = '''FILES:${PN} += "/usr/lib/systemd/system/*.service"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdHardcodedPathsRule()
        results = rule.check(context)
        
        # FILES paths should NOT be flagged by SYSTEMD003
        assert len(results) == 0

    def test_systemd_image_rootfs_inspection_not_flagged(self):
        """Test that systemd paths in IMAGE_ROOTFS inspection are NOT flagged.
        
        Image inspection code (ROOTFS_POSTPROCESS_COMMAND, QA checks) scans
        already-built images and needs literal paths to find/grep files.
        """
        from bake_linter.rules.systemd import SystemdHardcodedPathsRule
        
        content = '''check_services() {
    global_status=0
    # Find all .service files in systemd directories only (not symlinks)
    for service in $(find ${IMAGE_ROOTFS}/etc/systemd/system ${IMAGE_ROOTFS}/usr/lib/systemd/system -name "*.service" -type f 2>/dev/null); do
        service_name=$(basename "$service")
        # Check if service is in exclusion list
        skip_service=false
    done
}
'''
        context = FileContext(
            path=Path("test-image.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdHardcodedPathsRule()
        results = rule.check(context)
        
        # IMAGE_ROOTFS inspection should NOT be flagged - scanning built image
        assert len(results) == 0

    def test_systemd_image_rootfs_grep_not_flagged(self):
        """Test that grep commands with IMAGE_ROOTFS are NOT flagged."""
        from bake_linter.rules.systemd import SystemdHardcodedPathsRule
        
        content = '''validate_systemd() {
    # Check for enabled services
    grep -r "WantedBy" ${IMAGE_ROOTFS}/usr/lib/systemd/system/*.service
    
    # List all timers
    ls ${IMAGE_ROOTFS}/usr/lib/systemd/system/*.timer 2>/dev/null || true
}
'''
        context = FileContext(
            path=Path("test-image.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdHardcodedPathsRule()
        results = rule.check(context)
        
        # IMAGE_ROOTFS with grep/ls is inspection code - NOT flagged
        assert len(results) == 0

    def test_systemd_deploy_dir_inspection_not_flagged(self):
        """Test that systemd paths with DEPLOY_DIR are NOT flagged."""
        from bake_linter.rules.systemd import SystemdHardcodedPathsRule
        
        content = '''check_deployed_services() {
    # Inspect deployed image
    find ${DEPLOY_DIR_IMAGE}/rootfs/usr/lib/systemd/system -name "*.service"
}
'''
        context = FileContext(
            path=Path("test-image.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SystemdHardcodedPathsRule()
        results = rule.check(context)
        
        # DEPLOY_DIR inspection should NOT be flagged
        assert len(results) == 0


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
        # Non-recursive cp should suggest install -m MODE
        assert "install -d" in results[0].hint

    def test_cp_recursive_suggests_find_install(self):
        """Test that cp -r suggests find + install pattern."""
        from bake_linter.rules.install import CpInsteadOfInstallRule
        
        content = '''do_install() {
    install -m 0755 -d ${D}/etc/max
    cp -r ${WORKDIR}/git/www ${D}/etc/max
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
        # Recursive cp should suggest find + install
        assert "find" in results[0].hint
        assert "install" in results[0].hint

    def test_cp_recursive_variants(self):
        """Test that various recursive cp flags are detected."""
        from bake_linter.rules.install import CpInsteadOfInstallRule
        
        # Test -R flag
        content = '''do_install() {
    cp -R src ${D}/dest
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
        assert "find" in results[0].hint
        
        # Test -a flag (implies -r)
        content = '''do_install() {
    cp -a src ${D}/dest
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        results = rule.check(context)
        assert len(results) == 1
        assert "find" in results[0].hint
        
        # Test combined flags -rf
        content = '''do_install() {
    cp -rf src ${D}/dest
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        results = rule.check(context)
        assert len(results) == 1
        assert "find" in results[0].hint

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

    def test_install_with_combined_flags_ok(self):
        """Test that install with combined -Dm flag passes (not a false positive)."""
        from bake_linter.rules.install import InstallWithoutModeRule
        
        # All these valid patterns should pass
        content = '''do_install() {
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/country-code.service ${D}${systemd_unitdir}/system
    install -Dm 0644 ${WORKDIR}/country-code.in ${D}${sysconfdir}/country-code
    install -Dm0644 ${WORKDIR}/another.in ${D}${sysconfdir}/another
    install -D -m 0755 ${WORKDIR}/script.sh ${D}${bindir}/script.sh
    install -m0755 mybin ${D}${bindir}/mybin
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
        
        # None of these should be flagged - they all have explicit modes
        assert len(results) == 0

    def test_non_fhs_path_with_variable_not_flagged(self):
        """Test that ${D}/${bindir} is NOT flagged (FHS variable with extra slash)."""
        from bake_linter.rules.install import NonFHSPathRule
        
        content = '''do_install() {
    install -d ${D}/${bindir}
    install -m 0755 mybin ${D}/${bindir}/mybin
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = NonFHSPathRule()
        results = rule.check(context)
        
        # ${bindir} is FHS-compliant, extra slash is harmless
        assert len(results) == 0

    def test_non_fhs_path_various_variables_not_flagged(self):
        """Test that various FHS variable patterns are NOT flagged."""
        from bake_linter.rules.install import NonFHSPathRule
        
        content = '''do_install() {
    install -d ${D}/${bindir}
    install -d ${D}/${libdir}
    install -d ${D}/${sysconfdir}/myapp
    install -d ${D}/${datadir}/myapp
    install -d ${D}/${systemd_system_unitdir}
    install -d ${D}${bindir}
    install -d ${D}${libdir}/mylib
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = NonFHSPathRule()
        results = rule.check(context)
        
        # All FHS variables should be recognized as compliant
        assert len(results) == 0

    def test_non_fhs_path_literal_paths_not_flagged(self):
        """Test that literal FHS paths like /usr/bin are NOT flagged."""
        from bake_linter.rules.install import NonFHSPathRule
        
        content = '''do_install() {
    install -d ${D}/usr/bin
    install -d ${D}/etc/myapp
    install -d ${D}/var/lib/myapp
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = NonFHSPathRule()
        results = rule.check(context)
        
        # Literal FHS paths should be OK
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

    def test_srcrev_format_not_flagged(self):
        """Test that SRCREV_FORMAT is NOT flagged as unpinned.
        
        SRCREV_FORMAT is a special variable for multi-repo version formatting.
        It's a format string like "rkbin_tools", not a commit hash.
        """
        from bake_linter.rules.patch import SrcrevUnpinnedRule
        
        content = '''SRCREV_rkbin = "c41b714cacd249e3ef69b2bbe774da5095eefd72"
SRCREV_tools = "1a32bc776af52494144fcef6641a73850cee628a"
SRCREV_FORMAT ?= "rkbin_tools"
S = "${WORKDIR}/git"
'''
        context = FileContext(
            path=Path("firmware_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SrcrevUnpinnedRule()
        results = rule.check(context)
        
        # SRCREV_FORMAT should NOT be flagged - it's a format string, not a commit
        # The actual SRCREV_rkbin and SRCREV_tools are properly pinned
        assert len(results) == 0

    def test_srcrev_multi_repo_with_format(self):
        """Test multi-repo recipe with SRCREV_FORMAT passes."""
        from bake_linter.rules.patch import SrcrevUnpinnedRule
        
        content = '''SRC_URI = "git://example.com/rkbin.git;name=rkbin;branch=main \\
           git://example.com/tools.git;name=tools;branch=master;destsuffix=tools"

SRCREV_rkbin = "c41b714cacd249e3ef69b2bbe774da5095eefd72"
SRCREV_tools = "1a32bc776af52494144fcef6641a73850cee628a"
SRCREV_FORMAT = "rkbin_tools"
'''
        context = FileContext(
            path=Path("firmware_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SrcrevUnpinnedRule()
        results = rule.check(context)
        
        # All SRCREVs are properly pinned, FORMAT is a format string
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

    def test_pkgconfig_native_in_depends_ok(self):
        """Test that pkgconfig-native in DEPENDS does not flag (native build tool use)."""
        from bake_linter.rules.dependency import MissingPkgconfigInheritRule
        
        # This is the false positive case - pkgconfig-native is sufficient for native builds
        content = '''inherit cmake systemd
DEPENDS = "boost nlohmann-json libarchive fmt grpc systemd pkgconfig-native cli11"
'''
        context = FileContext(
            path=Path("usb-update-controller.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MissingPkgconfigInheritRule()
        results = rule.check(context)
        
        # Should NOT flag - pkgconfig-native is sufficient for build tool usage
        assert len(results) == 0

    def test_native_recipe_pkgconfig_ok(self):
        """Test that native recipes using pkgconfig are not flagged."""
        from bake_linter.rules.dependency import MissingPkgconfigInheritRule
        
        content = '''do_configure() {
    PKG_CONFIG_PATH="${STAGING_LIBDIR}/pkgconfig" oe_runconf
}
'''
        context = FileContext(
            path=Path("myapp-native_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MissingPkgconfigInheritRule()
        results = rule.check(context)
        
        # Should NOT flag - native recipes don't need cross-compilation setup
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
        """Test that unmatched quotes are flagged, but not for English text with apostrophes inside double quotes."""
        from bake_linter.rules.syntax import UnmatchedQuotesRule

        # Should flag: unmatched double quote
        content1 = 'DESCRIPTION = "This is missing a quote\n'
        context1 = FileContext(
            path=Path("test1_1.0.bb"),
            content=content1,
            lines=content1.splitlines(keepends=True),
            variables={},
        )
        rule = UnmatchedQuotesRule()
        results1 = rule.check(context1)
        assert len(results1) == 1
        assert results1[0].rule_id == "SYNTAX001"

        # Should NOT flag: English text with apostrophe inside double quotes
        content2 = 'DESCRIPTION = "This is a liberally licensed VNC server library that\'s intended to be fast and neat."\n'
        context2 = FileContext(
            path=Path("test2_1.0.bb"),
            content=content2,
            lines=content2.splitlines(keepends=True),
            variables={},
        )
        results2 = rule.check(context2)
        assert len(results2) == 0

        # Should NOT flag: English text with double quote inside single quotes
        content3 = "DESCRIPTION = 'This is a " + '\"' + "quote inside single quotes.'\n"
        context3 = FileContext(
            path=Path("test3_1.0.bb"),
            content=content3,
            lines=content3.splitlines(keepends=True),
            variables={},
        )
        results3 = rule.check(context3)
        assert len(results3) == 0

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

    def test_hardcoded_credentials_license_not_flagged(self):
        """Test that LICENSE with 'password' in package name is NOT flagged.
        
        Package names like passport-oauth2-client-password are legitimate
        and should not trigger credential detection.
        """
        from bake_linter.rules.security import HardcodedCredentialsRule
        
        content = '''LICENSE:${PN}-passport = "MIT"
LICENSE:${PN}-passport-http-bearer = "MIT"
LICENSE:${PN}-passport-oauth2-client-password = "MIT"
LICENSE:${PN}-passport-strategy = "MIT"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = HardcodedCredentialsRule()
        results = rule.check(context)
        
        # Should NOT flag - these are package names in LICENSE variables
        assert len(results) == 0

    def test_hardcoded_credentials_summary_not_flagged(self):
        """Test that SUMMARY/DESCRIPTION with credential words is NOT flagged."""
        from bake_linter.rules.security import HardcodedCredentialsRule
        
        content = '''SUMMARY = "Password management tool for secure password storage"
DESCRIPTION = "This tool helps manage api-key rotation and secret handling"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = HardcodedCredentialsRule()
        results = rule.check(context)
        
        # Should NOT flag - these are documentation variables
        assert len(results) == 0

    def test_hardcoded_credentials_placeholder_not_flagged(self):
        """Test that placeholder patterns like @PASSWORD@ are NOT flagged."""
        from bake_linter.rules.security import HardcodedCredentialsRule
        
        content = '''do_configure() {
    sed -i 's/@PASSWORD@/${DB_PASSWORD}/' config.ini
    echo "password = @PASSWORD@" > template.conf
    echo "api_key = ${API_KEY}" > config.env
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = HardcodedCredentialsRule()
        results = rule.check(context)
        
        # Should NOT flag - these are placeholder patterns
        assert len(results) == 0

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

    def test_build_path_leakage_runtime_env_ok(self):
        """Test that runtime environment variables written to ${D} are NOT flagged."""
        from bake_linter.rules.security import BuildPathLeakageRule
        
        # This is writing a runtime environment variable, NOT a build path leak
        content = '''do_install() {
    echo "export WAYLAND_DISPLAY=wayland-1" >> ${D}/home/user/.profile
    echo "export PATH=$PATH:/usr/local/bin" >> ${D}/etc/profile.d/myapp.sh
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
        
        # Should NOT flag - these are runtime env vars, not build path leaks
        assert len(results) == 0


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

    def test_shell_underscores_not_false_positive(self):
        """Test that underscores in shell commands don't trigger false positives.
        
        This tests the fix for the false positive where shell commands like
        'mining_app_install' were incorrectly detected as old override syntax.
        """
        from bake_linter.rules.syntax import MixedOverrideSyntaxRule
        
        # This is valid code using new :append syntax
        # The underscores in shell commands should NOT be flagged
        content = '''SUMMARY = "Test recipe"
LICENSE = "MIT"

do_install:append() {
    # Mining_app_install backwards compatibility
    ln -sr ${D}/${usrsrcdir}/mpkg/mpkg.install ${D}/${sbindir}/mining_app_install
    ln -sr ${D}/${usrsrcdir}/mpkg/mpkg.remove ${D}/${sbindir}/mining_app_remove
    ln -sr ${D}/${usrsrcdir}/mpkg/mpkg.list ${D}/${sbindir}/mining_app_list
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MixedOverrideSyntaxRule()
        results = rule.check(context)
        
        # Should have NO results - only new syntax is used (do_install:append)
        # Shell code with underscores should be ignored
        assert len(results) == 0, f"False positive detected: {results}"

    def test_shell_underscores_with_actual_mixed_syntax(self):
        """Test that actual mixed syntax is still detected even with shell underscores."""
        from bake_linter.rules.syntax import MixedOverrideSyntaxRule
        
        # This has BOTH old _append variable and new :append function
        content = '''SUMMARY = "Test recipe"
LICENSE = "MIT"
SRC_URI_append = " file://fix.patch"

do_install:append() {
    ln -sr ${D}/my_app_name ${D}/link
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MixedOverrideSyntaxRule()
        results = rule.check(context)
        
        # Should detect the mixed syntax (SRC_URI_append vs do_install:append)
        assert len(results) == 1
        assert results[0].rule_id == "SYNTAX005"
        assert "SRC_URI_append" in results[0].context

    def test_invalid_override_ordering_operation_after_conditional(self):
        """Test that operation AFTER conditional override is flagged.
        
        BitBake requires operations (:append/:prepend/:remove) to come BEFORE
        conditional overrides (:machine/:class-*/:pn-*).
        
        WRONG: VAR:qemux86-64:append = "value"  (conditional before operation)
        RIGHT: VAR:append:qemux86-64 = "value"  (operation before conditional)
        """
        from bake_linter.rules.syntax import InvalidOverrideOrderingRule
        
        content = '''CFLAGS:qemux86-64:append = " -DFOO"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = InvalidOverrideOrderingRule()
        results = rule.check(context)
        
        # Should flag - :append should come BEFORE :qemux86-64
        assert len(results) == 1
        assert results[0].rule_id == "SYNTAX006"
        assert "append" in results[0].message

    def test_invalid_override_ordering_class_before_prepend(self):
        """Test that class override before :prepend is flagged."""
        from bake_linter.rules.syntax import InvalidOverrideOrderingRule
        
        content = '''VAR:class-target:prepend = "value"
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
        assert "prepend" in results[0].message

    def test_invalid_override_ordering_pn_before_remove(self):
        """Test that pn override before :remove is flagged."""
        from bake_linter.rules.syntax import InvalidOverrideOrderingRule
        
        content = '''VAR:pn-recipe:remove = "value"
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
        assert "remove" in results[0].message

    def test_package_scope_before_operation_is_not_flagged(self):
        """A package-name override legitimately precedes the operation.

        This is the ubiquitous upstream convention (252 occurrences in the
        vendored poky/meta-openembedded trees); the reverse form the rule used
        to suggest (RDEPENDS:append:${PN}) appears there zero times.
        """
        from bake_linter.rules.syntax import InvalidOverrideOrderingRule

        content = '''RDEPENDS:${PN}:append:qemux86-64 = " example-app"
RDEPENDS:${PN}:append = " example-daemon"
RDEPENDS:${PN}-ptest:append = " bash"
FILES:${PN}:append:qemux86-64 = " /usr/share/foo"
INSANE_SKIP:${PN}:append:linux-gnux32 = " textrel"
RDEPENDS:packagegroup-meta-oe-support:append = " pkg"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )

        rule = InvalidOverrideOrderingRule()
        results = rule.check(context)

        assert results == []

    def test_conditional_before_operation_still_flagged_on_package_var(self):
        """A package-scoped variable does not excuse a *conditional* override
        placed before the operation."""
        from bake_linter.rules.syntax import InvalidOverrideOrderingRule

        content = '''WKS_FILE_DEPENDS:qemux86-64:append = " x"
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
        assert "qemux86-64" in results[0].message

    def test_valid_override_ordering_operation_first(self):
        """Test that operation BEFORE conditional override is NOT flagged.
        
        This is the correct BitBake syntax:
        VAR:append:machine = "value"
        VAR:prepend:class-target = "value"
        """
        from bake_linter.rules.syntax import InvalidOverrideOrderingRule
        
        content = '''WKS_FILE_DEPENDS:append:qemux86-64 = " example-initramfs"
RDEPENDS:append:${PN} = " bash"
DEPENDS:remove:class-native = "pkgconfig"
VAR:prepend:class-target = "value"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = InvalidOverrideOrderingRule()
        results = rule.check(context)
        
        # Should NOT flag - operations come first (correct order)
        assert len(results) == 0

    def test_valid_override_ordering_single_operation(self):
        """Test that single operation without conditional is NOT flagged."""
        from bake_linter.rules.syntax import InvalidOverrideOrderingRule
        
        content = '''VAR:append = "value"
VAR:prepend = "other"
VAR:remove = "item"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = InvalidOverrideOrderingRule()
        results = rule.check(context)
        
        # Should NOT flag - single operations are valid
        assert len(results) == 0

    def test_valid_override_ordering_just_conditional(self):
        """Test that just conditional override without operation is NOT flagged."""
        from bake_linter.rules.syntax import InvalidOverrideOrderingRule
        
        content = '''VAR:qemux86 = "value"
VAR:class-native = "other"
VAR:pn-myrecipe = "something"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = InvalidOverrideOrderingRule()
        results = rule.check(context)
        
        # Should NOT flag - just overrides without operations
        assert len(results) == 0

    def test_valid_override_ordering_multiple_conditionals(self):
        """Test that operation followed by multiple conditionals is NOT flagged."""
        from bake_linter.rules.syntax import InvalidOverrideOrderingRule
        
        content = '''VAR:append:qemux86:class-target = "value"
VAR:prepend:pn-recipe:qemuall = "value"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = InvalidOverrideOrderingRule()
        results = rule.check(context)
        
        # Should NOT flag - operation comes first, multiple conditionals after
        assert len(results) == 0


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

    def test_multiline_files_assignment_is_collected(self):
        """A FILES value written across continuation lines must be read whole.

        Reading only the first line saw an empty list and flagged every
        installed path in the recipe.
        """
        from bake_linter.rules.package import FilesNotMatchingInstallRule

        content = '''do_install() {
    install -d ${D}/opt/custom
    install -m 0755 mybin ${D}/opt/custom/mybin
}

FILES:${PN} = " \\
    /opt/custom \\
"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )

        rule = FilesNotMatchingInstallRule()
        results = rule.check(context)

        assert results == []

    def test_directory_whose_contents_are_packaged_is_covered(self):
        """Listing a directory's contents rather than the bare directory is the
        correct packaging pattern - packaging the directory itself would
        swallow the -dbg/-dev split - so `install -d` of it is covered."""
        from bake_linter.rules.package import FilesNotMatchingInstallRule

        content = '''do_install() {
    install -d ${D}/opt
    touch ${D}/opt/install.log
    install -d ${D}/usr/src/thing
    install -m 0644 server.py ${D}/usr/src/thing/server.py
}

FILES:${PN} = " \\
    /opt/install.log \\
    /usr/src/thing/server.py \\
"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )

        rule = FilesNotMatchingInstallRule()
        results = rule.check(context)

        assert results == []

    def test_uncovered_install_path_still_flagged(self):
        """A path that FILES genuinely does not cover is still a finding."""
        from bake_linter.rules.package import FilesNotMatchingInstallRule

        content = '''do_install() {
    install -d ${D}/opt/covered
    install -m 0755 a ${D}/opt/covered/a
    install -d ${D}/opt/forgotten
    install -m 0755 b ${D}/opt/forgotten/b
}

FILES:${PN} = " \\
    /opt/covered \\
"
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
        assert all(r.rule_id == "PKG002" for r in results)
        assert all("forgotten" in r.message for r in results)

    def test_find_exec_placeholder_is_not_a_path(self):
        """`find ... -exec install -d ${D}/dir/{} \\;` expands {} per match at
        build time, so the captured "path" is a shell placeholder that FILES
        can never name."""
        from bake_linter.rules.package import FilesNotMatchingInstallRule

        content = '''do_install() {
    install -d ${D}/usr/src/thing
    ( cd ${WORKDIR}/git && find server -type d -exec install -d ${D}/usr/src/thing/{} \\; )
    ( cd ${WORKDIR}/git && find server -type f -exec install -m 0644 {} ${D}/usr/src/thing/{} \\; )
}

FILES:${PN} = " \\
    /usr/src/thing/server \\
"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )

        rule = FilesNotMatchingInstallRule()
        results = rule.check(context)

        assert results == []

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

    def test_mutable_branch_with_pinned_srcrev_is_not_flagged(self):
        """A pinned SRCREV decides what gets built; the branch is only the ref
        bitbake fetches and validates against. Poky/meta-openembedded have 736
        recipes on branch=master|main, 728 of them (98.9%) pinned like this."""
        from bake_linter.rules.supply_chain import UnpinnedBranchRule

        content = '''SRC_URI = "git://github.com/foo/bar.git;branch=master;protocol=https"
SRCREV = "0123456789abcdef0123456789abcdef01234567"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )

        rule = UnpinnedBranchRule()
        results = rule.check(context)

        assert results == []

    def test_mutable_branch_with_autorev_is_flagged(self):
        """AUTOREV is the genuinely unreproducible case: it floats even though
        a SRCREV assignment is present."""
        from bake_linter.rules.supply_chain import UnpinnedBranchRule

        content = '''SRC_URI = "git://github.com/foo/bar.git;branch=master;protocol=https"
SRCREV = "${AUTOREV}"
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

    def test_bbappend_src_uri_without_lic_check(self):
        """Test that a bbappend fetching upstream source without a license
        check is flagged."""
        from bake_linter.rules.supply_chain import MissingLicenseChecksumInBbappendRule

        content = '''SRC_URI += "git://example.com/extra.git;branch=main"
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

    def test_bbappend_patch_only_src_uri_is_not_flagged(self):
        """A bbappend that only adds local files (patches, configs, units) is
        NOT flagged: LIC_FILES_CHKSUM pins the licence text of the *fetched
        upstream source*, and real poky/OE bbappends adding patches do not
        touch it."""
        from bake_linter.rules.supply_chain import MissingLicenseChecksumInBbappendRule

        content = '''FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://custom-patch.patch"
SRC_URI:append = " file://my.service"
'''
        context = FileContext(
            path=Path("test_%.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )

        rule = MissingLicenseChecksumInBbappendRule()
        results = rule.check(context)

        assert results == []

    def test_bbappend_src_uri_append_form_is_detected(self):
        """The :append form must be detected too - it is the most common way a
        bbappend adds sources, and the previous pattern silently missed it."""
        from bake_linter.rules.supply_chain import MissingLicenseChecksumInBbappendRule

        content = '''SRC_URI:append = " https://example.com/extra-1.0.tar.gz"
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

    def test_bbappend_remote_source_on_continuation_line_is_detected(self):
        """A remote fetch on a continuation line of the assignment counts."""
        from bake_linter.rules.supply_chain import MissingLicenseChecksumInBbappendRule

        content = '''SRC_URI += "\\
    file://local.patch \\
    git://example.com/extra.git;branch=main \\
"
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

    def test_shell_variable_flagged(self):
        """Test that unquoted shell variable $D is flagged."""
        from bake_linter.rules.task import UnquotedVariableRule
        
        # $D is a shell variable (no braces) - SHOULD be flagged
        content = '''do_install() {
    rm -rf $D/usr/lib/*
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
        
        # Should flag $D as unquoted shell variable
        assert any(r.rule_id == "TASK001" for r in results)
        assert any("$D" in r.message for r in results)

    def test_bitbake_variable_not_flagged(self):
        """Test that BitBake variable expansion ${D} is NOT flagged.
        
        ${VAR} is BitBake expansion - it's expanded BEFORE the shell sees it,
        so it's safe from word splitting. This is NOT a shell variable.
        """
        from bake_linter.rules.task import UnquotedVariableRule
        
        # ${D} is BitBake expansion (safe) - should NOT be flagged
        content = '''do_install() {
    install -d ${D}/${libexecdir}
    install -m 0755 ${WORKDIR}/${BPN}.py ${D}/${libexecdir}
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
        
        # Should NOT flag ${D} or ${WORKDIR} - they're BitBake expansions
        assert len(results) == 0

    def test_quoted_shell_variable_ok(self):
        """Test that quoted shell variable is NOT flagged."""
        from bake_linter.rules.task import UnquotedVariableRule
        
        content = '''do_install() {
    rm -rf "$D/usr/lib/*"
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
        
        # Should NOT flag - $D is properly quoted
        assert len(results) == 0

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

    def test_sudo_group_in_useradd_ok(self):
        """Test that 'sudo' as a Unix group name is NOT flagged (not a command)."""
        from bake_linter.rules.task import SudoUsageRule
        
        # 'sudo' here is a Unix group, not a command being executed
        content = '''USERADD_PARAM:${PN} = "-u 1010 -d /home/user -r -s /bin/bash -g user -G video,input,audio,dialout,sudo -p '${USER_HASH}' user"
USERADD_PARAM:${PN}-setup = "-u 1012 -d /home/setup -r -s /bin/bash -g setup -G sudo -p '${USER_HASH}' setup"
'''
        context = FileContext(
            path=Path("example-users_0.1.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SudoUsageRule()
        results = rule.check(context)
        
        # Should NOT flag - 'sudo' is a group name, not a command
        assert len(results) == 0

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

    def test_documentation_vars_paths_ok(self):
        """Test that paths in SUMMARY/DESCRIPTION are not flagged (just text, not code)."""
        from bake_linter.rules.portability import AbsoluteHostPathRule
        
        # These are documentation strings, not actual host path references
        content = '''SUMMARY = "Update /etc/hosts with entries from /etc/hosts.d"
DESCRIPTION = "Manages /usr/local/bin configuration and /opt/myapp settings"
LICENSE = "CLOSED"
'''
        context = FileContext(
            path=Path("update-hosts_0.1.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = AbsoluteHostPathRule()
        results = rule.check(context)
        
        # Should NOT flag - these are just text descriptions
        assert len(results) == 0

    def test_destdir_paths_ok(self):
        """Test that ${D}/usr/lib paths are not flagged (target filesystem via destdir)."""
        from bake_linter.rules.portability import AbsoluteHostPathRule
        
        # These paths are prefixed with ${D} - they're target filesystem, not host
        content = '''do_install:append() {
    sed -i '/^EnvironmentFile=/d' ${D}/usr/lib/systemd/system/discovery.service
    sed -i '/^ExecStart=/c\\ExecStart=/bin/sh -c . /etc/device_discovery/iface.setup' ${D}/usr/lib/systemd/system/discovery.service
    install -d ${D}/etc/myapp
}
'''
        context = FileContext(
            path=Path("myapp_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = AbsoluteHostPathRule()
        results = rule.check(context)
        
        # Should NOT flag - all paths are prefixed with ${D} (target destdir)
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


class TestUriRules:
    """Tests for URI and source rules."""

    def test_src_uri_protocol_consistency(self):
        """Test that mixed protocols are flagged."""
        from bake_linter.rules.uri import SrcUriProtocolConsistencyRule
        
        content = '''SRC_URI = "\\
    git://github.com/foo/bar.git;protocol=https \\
    git://github.com/foo/baz.git;protocol=git \\
"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SrcUriProtocolConsistencyRule()
        results = rule.check(context)
        
        assert len(results) >= 1
        assert results[0].rule_id == "URI001"

    def test_git_srcrev_invalid_format(self):
        """Test that invalid SRCREV format is flagged."""
        from bake_linter.rules.uri import GitSrcrevValidityRule
        
        content = '''SRC_URI = "git://github.com/project/repo.git;protocol=https"
SRCREV = "abc123"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = GitSrcrevValidityRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "URI002"

    def test_git_srcrev_valid_sha1(self):
        """Test that valid 40-char SRCREV passes."""
        from bake_linter.rules.uri import GitSrcrevValidityRule
        
        content = '''SRC_URI = "git://github.com/project/repo.git;protocol=https"
SRCREV = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = GitSrcrevValidityRule()
        results = rule.check(context)
        
        assert len(results) == 0

    def test_version_constraint_missing_parens(self):
        """Test that version constraint without parentheses is flagged."""
        from bake_linter.rules.uri import VersionConstraintSyntaxRule
        
        content = '''RDEPENDS:${PN} += "libfoo >= 1.0"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = VersionConstraintSyntaxRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "DEPENDS001"


class TestPackageRulesExtended:
    """Tests for extended package rules."""

    def test_files_packages_consistency(self):
        """Test that FILES for undefined package is flagged."""
        from bake_linter.rules.package import FilesPackagesConsistencyRule
        
        content = '''PACKAGES = "${PN} ${PN}-doc"
FILES:${PN} = "${bindir}/*"
FILES:${PN}-extra = "${datadir}/extra/*"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = FilesPackagesConsistencyRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "PKG004"

    def test_rdepends_package_existence(self):
        """Test that RDEPENDS for undefined package is flagged."""
        from bake_linter.rules.package import RdependsPackageExistenceRule
        
        content = '''PACKAGES = "${PN}"
RDEPENDS:${PN}-tools += "bash"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = RdependsPackageExistenceRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "PKG005"

    def test_rrecommends_package_validity(self):
        """Test that RRECOMMENDS for undefined package is flagged."""
        from bake_linter.rules.package import RrecommendsPackageValidityRule
        
        content = '''PACKAGES = "${PN}"
RRECOMMENDS:${PN}-utils += "extra-tools"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = RrecommendsPackageValidityRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "PKG006"

    def test_files_with_package_before_pn_not_flagged(self):
        """Test that FILES with PACKAGE_BEFORE_PN is NOT flagged.
        
        PACKAGE_BEFORE_PN automatically adds packages to PACKAGES before ${PN}.
        This is a valid and common pattern in Yocto recipes.
        """
        from bake_linter.rules.package import FilesPackagesConsistencyRule
        
        content = '''PACKAGE_BEFORE_PN += "${PN}-examples"
ALLOW_EMPTY:${PN}-examples = "1"
FILES:${PN}-examples = "${bindir}"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = FilesPackagesConsistencyRule()
        results = rule.check(context)
        
        # Should NOT flag ${PN}-examples - it's added via PACKAGE_BEFORE_PN
        assert len(results) == 0

    def test_rdepends_with_package_before_pn_not_flagged(self):
        """Test that RDEPENDS with PACKAGE_BEFORE_PN is NOT flagged."""
        from bake_linter.rules.package import RdependsPackageExistenceRule
        
        content = '''PACKAGE_BEFORE_PN += "${PN}-tools"
RDEPENDS:${PN}-tools += "bash"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = RdependsPackageExistenceRule()
        results = rule.check(context)
        
        # Should NOT flag ${PN}-tools - it's added via PACKAGE_BEFORE_PN
        assert len(results) == 0

    def test_files_with_packages_prepend_not_flagged(self):
        """Test that FILES with PACKAGES =+ (prepend) is NOT flagged."""
        from bake_linter.rules.package import FilesPackagesConsistencyRule
        
        content = '''PACKAGES =+ "${PN}-extra"
FILES:${PN}-extra = "${datadir}/extra/*"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = FilesPackagesConsistencyRule()
        results = rule.check(context)
        
        # Should NOT flag ${PN}-extra - it's added via PACKAGES =+
        assert len(results) == 0

    def test_rdepends_ptest_with_inherit_not_flagged(self):
        """Test that RDEPENDS:${PN}-ptest with 'inherit ptest' is NOT flagged.
        
        The ptest class automatically creates ${PN}-ptest package.
        """
        from bake_linter.rules.package import RdependsPackageExistenceRule
        
        content = '''inherit autotools pkgconfig ptest

do_install_ptest() {
    cp -r ${S}/tests ${D}${PTEST_PATH}
}

RDEPENDS:${PN}-ptest += " \\
    locale-base-en-us \\
    perl-module-b \\
    perl-module-base \\
"
'''
        context = FileContext(
            path=Path("curl_8.5.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = RdependsPackageExistenceRule()
        results = rule.check(context)
        
        # Should NOT flag - ptest class auto-creates ${PN}-ptest
        assert len(results) == 0

    def test_rdepends_ptest_without_inherit_flagged(self):
        """Test that RDEPENDS:${PN}-ptest WITHOUT 'inherit ptest' IS flagged."""
        from bake_linter.rules.package import RdependsPackageExistenceRule
        
        content = '''inherit autotools pkgconfig

RDEPENDS:${PN}-ptest += "bash"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = RdependsPackageExistenceRule()
        results = rule.check(context)
        
        # Should flag - no ptest inheritance, ${PN}-ptest doesn't exist
        assert len(results) == 1
        assert results[0].rule_id == "PKG005"


class TestVariablesRulesExtended:
    """Tests for extended variable rules."""

    def test_unused_variable_assignment(self):
        """Test that unused variable is flagged."""
        from bake_linter.rules.variables import UnusedVariableAssignmentRule
        
        content = '''OLD_VERSION = "1.0"
CURRENT_VERSION = "2.0"
PV = "${CURRENT_VERSION}"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = UnusedVariableAssignmentRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "VARIABLES003"
        assert "OLD_VERSION" in results[0].message

    def test_unused_variable_special_vars_excluded(self):
        """Test that special BitBake variables consumed by classes are not flagged."""
        from bake_linter.rules.variables import UnusedVariableAssignmentRule
        
        # These are consumed by features_check.bbclass, not referenced directly
        content = '''REQUIRED_DISTRO_FEATURES = "wayland"
CONFLICT_DISTRO_FEATURES = "x11"
SYSTEMD_SERVICE:${PN} = "myservice.service"
USERADD_PACKAGES = "${PN}"
UPSTREAM_CHECK_URI = "https://example.com"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = UnusedVariableAssignmentRule()
        results = rule.check(context)
        
        # None of these special variables should be flagged
        assert len(results) == 0

    def test_variable_redefinition(self):
        """Test that variable redefinition is flagged."""
        from bake_linter.rules.variables import VariableRedefinitionRule
        
        content = '''MY_VAR = "initial"
MY_VAR = "overridden"
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = VariableRedefinitionRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "VARIABLES004"

    def test_excessive_append_prepend(self):
        """Test that excessive append/prepend is flagged."""
        from bake_linter.rules.variables import ExcessiveAppendPrependRule
        
        content = '''CFLAGS:append = " -DA"
CFLAGS:prepend = "B "
CFLAGS:append = " -DC"
CFLAGS:prepend = "D "
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = ExcessiveAppendPrependRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "VARIABLES005"


class TestFunctionRules:
    """Tests for function rules."""

    def test_task_function_order(self):
        """Test that non-standard task order is flagged."""
        from bake_linter.rules.function import TaskFunctionOrderRule
        
        content = '''do_install() {
    install -d ${D}${bindir}
}

do_configure() {
    ./configure
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = TaskFunctionOrderRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "FUNCTION001"

    def test_python_shell_mixing(self):
        """Test that mixing Python and shell for same task is flagged."""
        from bake_linter.rules.function import PythonShellMixingRule
        
        content = '''do_custom() {
    echo "Shell version"
}

python do_custom() {
    bb.note("Python version")
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = PythonShellMixingRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "FUNCTION002"

    def test_empty_task_override(self):
        """Test that empty task override is flagged."""
        from bake_linter.rules.function import EmptyTaskOverrideRule
        
        content = '''do_configure:append() {
    # Nothing here
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = EmptyTaskOverrideRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "TASK004"


class TestSecurityRulesExtended2:
    """Tests for extended security rules."""

    def test_suid_binary_detection(self):
        """Test that SUID binary is flagged."""
        from bake_linter.rules.security import SuidSgidBinaryRule
        
        content = '''do_install() {
    install -m 0755 mytool ${D}${bindir}/
    chmod 4755 ${D}${bindir}/mytool
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SuidSgidBinaryRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "SECURITY008"

    def test_suid_with_justification_ok(self):
        """Test that SUID with security comment passes."""
        from bake_linter.rules.security import SuidSgidBinaryRule
        
        content = '''do_install() {
    install -m 0755 mytool ${D}${bindir}/
    # SECURITY: SUID required for network access
    chmod 4755 ${D}${bindir}/mytool
}
'''
        context = FileContext(
            path=Path("test_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = SuidSgidBinaryRule()
        results = rule.check(context)
        
        assert len(results) == 0


class TestBbappendRulesExtended2:
    """Tests for extended bbappend rules."""

    def test_global_variable_in_bbappend(self):
        """Test that global variable in bbappend is flagged."""
        from bake_linter.rules.bbappend import GlobalVariableInBbappendRule
        
        content = '''TMPDIR = "/custom/tmp"
SRC_URI += "file://patch.patch"
'''
        context = FileContext(
            path=Path("recipe_%.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = GlobalVariableInBbappendRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "BBAPPEND005"

    def test_recipe_specific_var_ok(self):
        """Test that recipe-specific variable in bbappend passes."""
        from bake_linter.rules.bbappend import GlobalVariableInBbappendRule
        
        content = '''RDEPENDS:${PN} += "custom-lib"
SRC_URI += "file://patch.patch"
'''
        context = FileContext(
            path=Path("recipe_%.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = GlobalVariableInBbappendRule()
        results = rule.check(context)

        assert len(results) == 0

    def test_parallel_make_in_bbappend_is_not_flagged(self):
        """PARALLEL_MAKE is a documented per-recipe variable, the supported way
        to limit parallelism for a build system that cannot handle it. Poky
        sets it directly in recipes (glibc.inc, ovmf_git.bb, mtd-utils_git.bb,
        slang_2.3.3.bb, net-tools_2.10.bb), so a .bbappend setting it is not a
        misplaced global. BB_NUMBER_THREADS still is."""
        from bake_linter.rules.bbappend import GlobalVariableInBbappendRule

        content = '''PARALLEL_MAKE = "-j 1"
'''
        context = FileContext(
            path=Path("recipe_%.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )

        rule = GlobalVariableInBbappendRule()
        results = rule.check(context)

        assert results == []

    def test_bb_number_threads_in_bbappend_still_flagged(self):
        """The genuinely build-wide sibling of PARALLEL_MAKE stays flagged."""
        from bake_linter.rules.bbappend import GlobalVariableInBbappendRule

        content = '''BB_NUMBER_THREADS = "4"
'''
        context = FileContext(
            path=Path("recipe_%.bbappend"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )

        rule = GlobalVariableInBbappendRule()
        results = rule.check(context)

        assert len(results) == 1
        assert results[0].rule_id == "BBAPPEND005"


class TestLayerRules:
    """Tests for layer configuration rules."""

    def test_missing_layerseries_compat(self):
        """Test that missing LAYERSERIES_COMPAT is flagged."""
        from bake_linter.rules.layer import LayerseriesCompatRule
        
        content = '''BBFILE_COLLECTIONS += "mylayer"
BBFILE_PATTERN_mylayer = "^${LAYERDIR}/"
'''
        context = FileContext(
            path=Path("conf/layer.conf"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = LayerseriesCompatRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "LAYER001"

    def test_invalid_release_name(self):
        """Test that invalid release name is flagged."""
        from bake_linter.rules.layer import LayerseriesCompatRule
        
        content = '''BBFILE_COLLECTIONS += "mylayer"
LAYERSERIES_COMPAT_mylayer = "invalid-release scarthgap"
'''
        context = FileContext(
            path=Path("conf/layer.conf"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = LayerseriesCompatRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "LAYER001"
        assert "invalid-release" in results[0].message

    def test_valid_layerseries_compat(self):
        """Test that valid LAYERSERIES_COMPAT passes."""
        from bake_linter.rules.layer import LayerseriesCompatRule
        
        content = '''BBFILE_COLLECTIONS += "mylayer"
LAYERSERIES_COMPAT_mylayer = "kirkstone scarthgap"
'''
        context = FileContext(
            path=Path("conf/layer.conf"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = LayerseriesCompatRule()
        results = rule.check(context)
        
        assert len(results) == 0


class TestLifecycleRules:
    """Tests for lifecycle/maintenance rules."""

    def test_missing_upstream_check(self):
        """Test that missing UPSTREAM_CHECK is flagged."""
        from bake_linter.rules.lifecycle import MissingUpstreamCheckRule
        
        content = '''SUMMARY = "My package"
SRC_URI = "https://example.com/releases/foo-${PV}.tar.gz"
'''
        context = FileContext(
            path=Path("foo_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )
        
        rule = MissingUpstreamCheckRule()
        results = rule.check(context)
        
        assert len(results) == 1
        assert results[0].rule_id == "LIFECYCLE001"

    def test_with_upstream_check_ok(self):
        """Test that recipe with UPSTREAM_CHECK passes."""
        from bake_linter.rules.lifecycle import MissingUpstreamCheckRule
        
        content = '''SUMMARY = "My package"
SRC_URI = "https://example.com/releases/foo-${PV}.tar.gz"
UPSTREAM_CHECK_URI = "https://example.com/releases/"
UPSTREAM_CHECK_REGEX = "foo-(?P<pver>\\d+\\.\\d+)\\.tar\\.gz"
'''
        context = FileContext(
            path=Path("foo_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )

        rule = MissingUpstreamCheckRule()
        results = rule.check(context)

        assert len(results) == 0

    def test_closed_license_recipe_is_exempt(self):
        """A proprietary recipe has no public release feed for
        UPSTREAM_CHECK_* to point at. Of the 12 LICENSE = "CLOSED" recipes in
        the vendored poky/meta-openembedded trees, zero set any
        UPSTREAM_CHECK variable."""
        from bake_linter.rules.lifecycle import MissingUpstreamCheckRule

        content = '''SUMMARY = "internal daemon"
LICENSE = "CLOSED"
SRC_URI = "git://git.example.com/org/thing.git;protocol=ssh;branch=master"
SRCREV = "0123456789abcdef0123456789abcdef01234567"
'''
        context = FileContext(
            path=Path("thing_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )

        rule = MissingUpstreamCheckRule()
        results = rule.check(context)

        assert results == []

    def test_compound_closed_license_recipe_is_exempt(self):
        """CLOSED as a term in a compound expression counts: a partly
        proprietary recipe has no single public release index either. Found on
        a recipe, whose LICENSE is "CLOSED & GPL-2.0-or-later"."""
        from bake_linter.rules.lifecycle import MissingUpstreamCheckRule

        content = '''SUMMARY = "internal lib with a GPL part"
LICENSE = "CLOSED & GPL-2.0-or-later"
SRC_URI = "git://git.example.com/org/lib.git;protocol=ssh;branch=master"
SRCREV = "0123456789abcdef0123456789abcdef01234567"
'''
        context = FileContext(
            path=Path("lib_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )

        rule = MissingUpstreamCheckRule()
        results = rule.check(context)

        assert results == []

    def test_open_license_recipe_still_flagged(self):
        """A recipe tracking a public upstream is still expected to declare
        UPSTREAM_CHECK_*."""
        from bake_linter.rules.lifecycle import MissingUpstreamCheckRule

        content = '''SUMMARY = "public thing"
LICENSE = "MIT"
SRC_URI = "https://example.com/releases/foo-${PV}.tar.gz"
'''
        context = FileContext(
            path=Path("foo_1.0.bb"),
            content=content,
            lines=content.splitlines(keepends=True),
            variables={},
        )

        rule = MissingUpstreamCheckRule()
        results = rule.check(context)

        assert len(results) == 1
        assert results[0].rule_id == "LIFECYCLE001"
