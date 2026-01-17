"""
Package rules for Yocto recipes.

These rules check for proper package configuration and dependencies.
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
