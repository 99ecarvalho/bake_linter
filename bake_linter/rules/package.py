# -*- coding: utf-8 -*-
"""
Package rules for Yocto recipes.

These rules check for proper package configuration and dependencies.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class RdependsOnDevPackageRule(BaseRule):
    """
    Check for -dev packages in RDEPENDS.
    
    -dev packages contain headers and static libraries for development
    and must never be runtime dependencies.
    """
    
    rule_id = "PKG001"
    name = "RDEPENDS on Development Package"
    description = "Detects -dev packages incorrectly in RDEPENDS"
    default_severity = Severity.ERROR
    groups = ["packaging", "dependency"]
    hint = "Move -dev packages to DEPENDS, use runtime library in RDEPENDS"

    RDEPENDS_PATTERN = re.compile(r'^RDEPENDS[_:]')
    DEV_PACKAGE_PATTERN = re.compile(r'\b(\S+-dev)\b')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if self.RDEPENDS_PATTERN.match(stripped):
                matches = self.DEV_PACKAGE_PATTERN.findall(stripped)
                for dev_pkg in matches:
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message=f"Development package '{dev_pkg}' in RDEPENDS (should be build-time only)",
                        context=stripped[:60],
                        hint=f"Move '{dev_pkg}' to DEPENDS; use runtime library in RDEPENDS",
                    ))
        
        return results


class FilesNotMatchingInstallRule(BaseRule):
    """
    Check for files installed to non-standard paths not covered by FILES.
    
    Files installed to custom paths need explicit FILES entries to be packaged.
    """
    
    rule_id = "PKG002"
    name = "FILES Not Matching Installed Paths"
    description = "Detects installed files that may not be covered by FILES"
    default_severity = Severity.WARNING
    groups = ["packaging"]
    hint = "Add matching FILES entry for installed paths"

    # Standard paths that are auto-covered by default FILES
    STANDARD_PATHS = [
        '${bindir}', '${sbindir}', '${libdir}', '${libexecdir}',
        '${datadir}', '${sysconfdir}', '${localstatedir}',
        '${includedir}', '${docdir}', '${mandir}', '${infodir}',
        '${systemd_system_unitdir}', '${systemd_user_unitdir}',
        '/usr/', '/etc/', '/var/', '/lib/', '/run/',
    ]
    
    INSTALL_TASK_PATTERN = re.compile(r'^do_install(?:[_:]|$|\s*\(\))')
    INSTALL_CMD_PATTERN = re.compile(r'install\s+.*\$\{D\}(/\S+)')
    FILES_PATTERN = re.compile(r'^FILES[_:]\$\{PN\}')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_do_install = False
        brace_depth = 0
        
        # Collect non-standard install paths
        custom_installs = []
        files_entries = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Collect FILES entries
            if self.FILES_PATTERN.match(stripped):
                files_entries.append(stripped)
            
            # Track do_install
            if self.INSTALL_TASK_PATTERN.match(stripped):
                in_do_install = True
                if '{' in stripped:
                    brace_depth = 1
                continue
            
            if in_do_install:
                brace_depth += stripped.count('{') - stripped.count('}')
                if brace_depth <= 0:
                    in_do_install = False
                    brace_depth = 0
                    continue
                
                # Find install commands
                match = self.INSTALL_CMD_PATTERN.search(line)
                if match:
                    install_path = match.group(1)
                    
                    # Check if standard path
                    is_standard = False
                    for std_path in self.STANDARD_PATHS:
                        if std_path in line or install_path.startswith(std_path.replace('${', '').replace('}', '')):
                            is_standard = True
                            break
                    
                    if not is_standard:
                        custom_installs.append((line_num, install_path))
        
        # Check custom installs against FILES
        for line_num, install_path in custom_installs:
            path_covered = False
            for files_entry in files_entries:
                if install_path in files_entry:
                    path_covered = True
                    break
                # Check parent directory coverage
                parts = install_path.split('/')
                for i in range(2, len(parts)):
                    parent = '/'.join(parts[:i])
                    if parent in files_entry or f"{parent}/*" in files_entry:
                        path_covered = True
                        break
            
            if not path_covered:
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message=f"Installed path '{install_path}' may not be covered by FILES",
                    hint=f'Add: FILES:${{PN}} += "{install_path}"',
                ))
        
        return results


class WildcardBbappendOverreachRule(BaseRule):
    """
    Check for version-wildcard bbappend files with version-specific modifications.
    
    Using recipe_%.bbappend with version-specific patches may cause issues
    when applied to incompatible recipe versions.
    """
    
    rule_id = "PKG003"
    name = "Wildcard bbappend Overreach"
    description = "Detects wildcard .bbappend with version-specific changes"
    default_severity = Severity.WARNING
    groups = ["packaging", "bbappend"]
    hint = "Use more specific version pattern or conditional logic"
    
    applicable_file_types = {"bbappend"}

    # Version-specific indicators
    VERSION_SPECIFIC_PATTERNS = [
        re.compile(r'fix.*v?\d+\.\d+', re.IGNORECASE),  # Patches mentioning versions
        re.compile(r'patch.*v?\d+\.\d+', re.IGNORECASE),
        re.compile(r'SRCREV\s*='),  # SRCREV changes
        re.compile(r'PV\s*='),  # PV overrides
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Only check wildcard bbappends
        filename = context.path.name
        if not filename.endswith('.bbappend'):
            return results
        
        if '%' not in filename:
            return results  # Not a wildcard append
        
        # Check for version-specific content
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            for pattern in self.VERSION_SPECIFIC_PATTERNS:
                if pattern.search(stripped):
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message="Wildcard bbappend with potentially version-specific content",
                        context=stripped[:60],
                        hint="Consider using recipe_X.%.bbappend for version-specific changes",
                    ))
                    return results  # One warning per file
        
        return results


class FilesPackagesConsistencyRule(BaseRule):
    """
    Check that FILES entries correspond to packages in PACKAGES.
    
    Each FILES:${PN}-foo must have corresponding ${PN}-foo in PACKAGES.
    
    IMPORTANT: This rule recognizes multiple ways to add packages:
    - PACKAGES = "..." or PACKAGES += "..." or PACKAGES =+ "..."
    - PACKAGE_BEFORE_PN += "..." (auto-adds to PACKAGES before ${PN})
    - PACKAGES_DYNAMIC = "..." (dynamic package generation)
    """
    
    rule_id = "PKG004"
    name = "FILES and PACKAGES Consistency"
    description = "Verifies FILES entries match packages defined in PACKAGES"
    default_severity = Severity.WARNING
    groups = ["packaging", "consistency"]
    hint = "Add missing package to PACKAGES or remove orphaned FILES"

    FILES_PATTERN = re.compile(r'^FILES[_:]([\w${}-]+)')
    PACKAGES_PATTERN = re.compile(r'^PACKAGES\s*[+=:]+')
    PACKAGE_BEFORE_PN_PATTERN = re.compile(r'^PACKAGE_BEFORE_PN\s*[+=:]+')
    PACKAGES_DYNAMIC_PATTERN = re.compile(r'^PACKAGES_DYNAMIC\s*[+=:]+')
    
    # Standard auto-generated packages
    STANDARD_PACKAGES = [
        '${PN}', '${PN}-dev', '${PN}-dbg', '${PN}-doc', '${PN}-staticdev',
        '${PN}-locale', '${PN}-src', '${PN}-lic',
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        files_packages: List[tuple] = []  # (line_num, package_name)
        packages_list: List[str] = []
        dynamic_patterns: List[str] = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Collect FILES entries
            match = self.FILES_PATTERN.match(stripped)
            if match:
                pkg_name = match.group(1)
                files_packages.append((line_num, pkg_name))
            
            # Collect PACKAGES entries (=, +=, =+, :=)
            if self.PACKAGES_PATTERN.match(stripped):
                # Extract package names
                value = stripped.split('=', 1)[1] if '=' in stripped else ''
                packages_list.extend(re.findall(r'[\w${}-]+', value))
            
            # Collect PACKAGE_BEFORE_PN entries (auto-adds to PACKAGES)
            if self.PACKAGE_BEFORE_PN_PATTERN.match(stripped):
                value = stripped.split('=', 1)[1] if '=' in stripped else ''
                packages_list.extend(re.findall(r'[\w${}-]+', value))
            
            # Collect PACKAGES_DYNAMIC patterns
            if self.PACKAGES_DYNAMIC_PATTERN.match(stripped):
                value = stripped.split('=', 1)[1] if '=' in stripped else ''
                # Extract patterns (may be regex-like)
                dynamic_patterns.extend(re.findall(r'[\w${}\-.*^]+', value))
        
        # Check each FILES entry
        for line_num, pkg_name in files_packages:
            # Skip standard packages
            if pkg_name in self.STANDARD_PACKAGES:
                continue
            
            # Check if package is in PACKAGES or PACKAGE_BEFORE_PN
            if pkg_name in packages_list:
                continue
            
            # Check if any pattern contains package name
            if any(pkg_name in p for p in packages_list):
                continue
            
            # Check if matched by PACKAGES_DYNAMIC pattern
            is_dynamic = False
            for dyn_pattern in dynamic_patterns:
                # Convert BitBake dynamic pattern to regex
                # e.g., "${PN}-locale-.*" or "lib.*"
                regex_pattern = dyn_pattern.replace('${PN}', r'.*').replace('.', r'\.').replace('*', '.*')
                try:
                    if re.match(regex_pattern, pkg_name):
                        is_dynamic = True
                        break
                except re.error:
                    pass  # Invalid regex, skip
            
            if is_dynamic:
                continue
            
            results.append(self.create_result(
                file=context.path,
                line=line_num,
                message=f"FILES:{pkg_name} defined but '{pkg_name}' not in PACKAGES",
                hint=f'Add: PACKAGES += "{pkg_name}" or PACKAGE_BEFORE_PN += "{pkg_name}"',
            ))
        
        return results


class RdependsPackageExistenceRule(BaseRule):
    """
    Check that packages in RDEPENDS:pkg are defined in PACKAGES.
    
    RDEPENDS:${PN}-foo requires ${PN}-foo to exist in PACKAGES.
    
    Recognizes packages added via:
    - PACKAGES = "..." or PACKAGES += "..." or PACKAGES =+ "..."
    - PACKAGE_BEFORE_PN += "..."
    - Inherited classes that auto-create packages (ptest, etc.)
    """
    
    rule_id = "PKG005"
    name = "RDEPENDS Package Existence"
    description = "Ensures packages referenced in RDEPENDS:pkg are in PACKAGES"
    default_severity = Severity.ERROR
    groups = ["packaging", "dependency"]
    hint = "Add package to PACKAGES or fix package name"

    RDEPENDS_PKG_PATTERN = re.compile(r'^RDEPENDS[_:]([\w${}-]+)')
    PACKAGES_PATTERN = re.compile(r'^PACKAGES\s*[+=:]+')
    PACKAGE_BEFORE_PN_PATTERN = re.compile(r'^PACKAGE_BEFORE_PN\s*[+=:]+')
    
    # Standard packages that always exist
    STANDARD_PACKAGES = ['${PN}', '${PN}-dev', '${PN}-dbg', '${PN}-doc', 
                         '${PN}-staticdev', '${PN}-locale']
    
    # Classes that auto-create packages: (class_name, package_suffix)
    # When a recipe inherits these classes, the corresponding package is auto-created
    CLASS_AUTO_PACKAGES = {
        'ptest': '${PN}-ptest',
        'python3-dir': '${PN}-staticdev',
        'kernel': '${KERNEL_PACKAGE_NAME}-base',
    }

    def _get_inherited_classes(self, context: FileContext) -> set:
        """Extract all inherited classes from the recipe."""
        classes = set()
        for line in context.lines:
            stripped = line.strip()
            if stripped.startswith('inherit'):
                # Extract class names from "inherit foo bar baz"
                parts = stripped.split()
                classes.update(parts[1:])  # Skip 'inherit' keyword
        return classes

    def _get_auto_created_packages(self, inherited_classes: set) -> set:
        """Get packages auto-created by inherited classes."""
        auto_packages = set()
        for class_name, pkg_pattern in self.CLASS_AUTO_PACKAGES.items():
            if class_name in inherited_classes:
                auto_packages.add(pkg_pattern)
        return auto_packages

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        rdepends_packages: List[tuple] = []
        packages_list: List[str] = []
        
        # Get auto-created packages from inherited classes
        inherited_classes = self._get_inherited_classes(context)
        auto_packages = self._get_auto_created_packages(inherited_classes)
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Collect RDEPENDS:pkg entries
            match = self.RDEPENDS_PKG_PATTERN.match(stripped)
            if match:
                pkg_name = match.group(1)
                rdepends_packages.append((line_num, pkg_name))
            
            # Collect PACKAGES entries (=, +=, =+, :=)
            if self.PACKAGES_PATTERN.match(stripped):
                value = stripped.split('=', 1)[1] if '=' in stripped else ''
                packages_list.extend(re.findall(r'[\w${}-]+', value))
            
            # Collect PACKAGE_BEFORE_PN entries (auto-adds to PACKAGES)
            if self.PACKAGE_BEFORE_PN_PATTERN.match(stripped):
                value = stripped.split('=', 1)[1] if '=' in stripped else ''
                packages_list.extend(re.findall(r'[\w${}-]+', value))
        
        for line_num, pkg_name in rdepends_packages:
            # Skip standard packages
            if pkg_name in self.STANDARD_PACKAGES:
                continue
            
            # Skip packages auto-created by inherited classes
            if pkg_name in auto_packages:
                continue
            
            if pkg_name not in packages_list and not any(pkg_name in p for p in packages_list):
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message=f"RDEPENDS:{pkg_name} but '{pkg_name}' not defined in PACKAGES",
                    hint=f'Add: PACKAGES += "{pkg_name}" or PACKAGE_BEFORE_PN += "{pkg_name}"',
                ))
        
        return results


class RrecommendsPackageValidityRule(BaseRule):
    """
    Check that packages in RRECOMMENDS:pkg are defined in PACKAGES.
    
    Similar to PKG005 but for RRECOMMENDS (lower severity).
    
    Recognizes packages added via:
    - PACKAGES = "..." or PACKAGES += "..." or PACKAGES =+ "..."
    - PACKAGE_BEFORE_PN += "..."
    """
    
    rule_id = "PKG006"
    name = "RRECOMMENDS Package Validity"
    description = "Checks packages in RRECOMMENDS:pkg are defined in PACKAGES"
    default_severity = Severity.INFO
    groups = ["packaging", "dependency"]
    hint = "Add package to PACKAGES or fix package name"

    RRECOMMENDS_PKG_PATTERN = re.compile(r'^RRECOMMENDS[_:]([\w${}-]+)')
    PACKAGES_PATTERN = re.compile(r'^PACKAGES\s*[+=:]+')
    PACKAGE_BEFORE_PN_PATTERN = re.compile(r'^PACKAGE_BEFORE_PN\s*[+=:]+')
    
    STANDARD_PACKAGES = ['${PN}', '${PN}-dev', '${PN}-dbg', '${PN}-doc']

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        rrecommends_packages: List[tuple] = []
        packages_list: List[str] = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            match = self.RRECOMMENDS_PKG_PATTERN.match(stripped)
            if match:
                pkg_name = match.group(1)
                rrecommends_packages.append((line_num, pkg_name))
            
            # Collect PACKAGES entries (=, +=, =+, :=)
            if self.PACKAGES_PATTERN.match(stripped):
                value = stripped.split('=', 1)[1]
                packages_list.extend(re.findall(r'[\w${}-]+', value))
            
            # Collect PACKAGE_BEFORE_PN entries (auto-adds to PACKAGES)
            if self.PACKAGE_BEFORE_PN_PATTERN.match(stripped):
                value = stripped.split('=', 1)[1] if '=' in stripped else ''
                packages_list.extend(re.findall(r'[\w${}-]+', value))
        
        for line_num, pkg_name in rrecommends_packages:
            if pkg_name in self.STANDARD_PACKAGES:
                continue
            
            if pkg_name not in packages_list and not any(pkg_name in p for p in packages_list):
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message=f"RRECOMMENDS:{pkg_name} but '{pkg_name}' not in PACKAGES",
                    hint=f'Verify package name or add: PACKAGES += "{pkg_name}" or PACKAGE_BEFORE_PN += "{pkg_name}"',
                ))
        
        return results
