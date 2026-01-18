# -*- coding: utf-8 -*-
"""
Code quality and style rules for Yocto recipes.

These rules check for general code quality issues and style violations.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class TrailingWhitespaceRule(BaseRule):
    """
    Check for trailing whitespace in recipe files.
    """
    
    rule_id = "STYLE001"
    name = "Trailing Whitespace"
    description = "Check for trailing whitespace"
    default_severity = Severity.INFO
    groups = ["style", "whitespace"]
    enabled_by_default = False  # Can be noisy
    hint = "Remove trailing whitespace"

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            if line.rstrip() != line.rstrip("\n\r"):
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message="Line has trailing whitespace",
                ))
        
        return results


class LongLineRule(BaseRule):
    """
    Check for excessively long lines.
    """
    
    rule_id = "STYLE002"
    name = "Long Lines"
    description = "Check for lines exceeding maximum length"
    default_severity = Severity.INFO
    groups = ["style"]
    enabled_by_default = False
    hint = "Consider breaking long lines using backslash continuation"

    # Default max line length
    DEFAULT_MAX_LENGTH = 120

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        max_length = self.get_option("max_length", self.DEFAULT_MAX_LENGTH)
        
        for line_num, line in enumerate(context.lines, start=1):
            if len(line.rstrip()) > max_length:
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message=f"Line exceeds {max_length} characters ({len(line.rstrip())} chars)",
                ))
        
        return results


class HardcodedPathsRule(BaseRule):
    """
    Check for hardcoded paths that should use variables.
    
    IMPORTANT: This rule skips documentation variables (SUMMARY, DESCRIPTION, etc.)
    where literal paths like /etc/hosts are appropriate for human readability.
    Users reading package descriptions need to see actual paths, not variables.
    
    Only flags hardcoded paths in actual code contexts:
    - Shell task implementations (do_install, do_configure, etc.)
    - FILES variable assignments
    - Other operational variables
    """
    
    rule_id = "STYLE003"
    name = "Hardcoded Paths"
    description = "Detect hardcoded paths that should use BitBake variables"
    default_severity = Severity.WARNING
    groups = ["style", "portability"]

    # Patterns for hardcoded paths and their suggested replacements
    HARDCODED_PATTERNS = [
        (re.compile(r'/usr/lib(?![a-z])'), "Use ${libdir} instead of /usr/lib"),
        (re.compile(r'/usr/bin(?![a-z])'), "Use ${bindir} instead of /usr/bin"),
        (re.compile(r'/usr/include(?![a-z])'), "Use ${includedir} instead of /usr/include"),
        (re.compile(r'/usr/share(?![a-z])'), "Use ${datadir} instead of /usr/share"),
        (re.compile(r'/etc(?![a-z])'), "Use ${sysconfdir} instead of /etc"),
        (re.compile(r'/var(?![a-z])'), "Use ${localstatedir} instead of /var"),
    ]
    
    # Documentation variables where literal paths are appropriate
    # These describe what software does, not how to build it
    DOCUMENTATION_VARS = [
        'SUMMARY', 'DESCRIPTION', 'HOMEPAGE', 'BUGTRACKER',
        'AUTHOR', 'MAINTAINER', 'SECTION', 'CVE_PRODUCT',
    ]
    
    # Pattern to detect documentation variable assignment
    DOC_VAR_PATTERN = re.compile(r'^(' + '|'.join(DOCUMENTATION_VARS) + r')\s*[+:]?=')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            # Skip SRC_URI lines (URLs legitimately contain paths)
            if "SRC_URI" in line:
                continue
            
            # Skip documentation variables (SUMMARY, DESCRIPTION, etc.)
            # Literal paths are appropriate for human-readable documentation
            if self.DOC_VAR_PATTERN.match(stripped):
                continue
            
            for pattern, message in self.HARDCODED_PATTERNS:
                if pattern.search(line):
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message=message,
                        context=stripped[:60],
                    ))
                    break  # One warning per line is enough
        
        return results


class TodoFixmeRule(BaseRule):
    """
    Flag TODO, FIXME, and XXX comments.
    """
    
    rule_id = "STYLE004"
    name = "TODO/FIXME Detection"
    description = "Flag TODO, FIXME, and XXX comments"
    default_severity = Severity.INFO
    groups = ["style", "todo"]
    enabled_by_default = False

    TODO_PATTERN = re.compile(r'#.*\b(TODO|FIXME|XXX|HACK)\b', re.IGNORECASE)

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            match = self.TODO_PATTERN.search(line)
            if match:
                marker = match.group(1).upper()
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message=f"{marker} comment found",
                    context=line.strip()[:60],
                    hint="Address the TODO/FIXME before release",
                ))
        
        return results


class EmptyVariableRule(BaseRule):
    """
    Check for empty variable assignments.
    """
    
    rule_id = "STYLE005"
    name = "Empty Variable Assignment"
    description = "Flag empty variable assignments"
    default_severity = Severity.INFO
    groups = ["style"]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for var_name, assignments in context.variables.items():
            for assignment in assignments:
                if not assignment.value.strip() and assignment.operator == "=":
                    # Skip known intentionally empty variables
                    if var_name in {"SRC_URI", "DEPENDS", "RDEPENDS"}:
                        continue
                    
                    results.append(self.create_result(
                        file=context.path,
                        line=assignment.line,
                        message=f"Empty assignment for '{var_name}'",
                        hint="Remove if intentionally empty, or add a comment explaining why",
                    ))
        
        return results


class DuplicateInheritRule(BaseRule):
    """
    Check for duplicate inherit statements.
    """
    
    rule_id = "STYLE006"
    name = "Duplicate Inherit"
    description = "Check for duplicate inherit class references"
    default_severity = Severity.WARNING
    groups = ["style", "redundancy"]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        seen_classes = {}  # class name -> first line number
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("inherit"):
                classes = stripped.split()[1:]
                for cls in classes:
                    if cls in seen_classes:
                        results.append(self.create_result(
                            file=context.path,
                            line=line_num,
                            message=f"Duplicate inherit of '{cls}' (first seen line {seen_classes[cls]})",
                            hint="Remove the duplicate inherit statement",
                        ))
                    else:
                        seen_classes[cls] = line_num
        
        return results


class PackageListFormatRule(BaseRule):
    """
    Check that package lists follow proper formatting conventions.
    
    Expected format:
    - Opening line has only the variable, '= "' and backslash
    - Each package on its own line, indented
    - Packages in alphabetical order
    - Closing line has only the closing quote
    - One blank line after the closing quote
    
    Example:
        IMAGE_INSTALL:append = " \\
            package-a \\
            package-b \\
            package-c \\
        "
    """
    
    rule_id = "STYLE007"
    name = "Package List Format"
    description = "Check package list formatting (alphabetical, one per line)"
    default_severity = Severity.WARNING
    groups = ["style", "formatting"]
    hint = "Format package lists with one package per line in alphabetical order"

    # Variables that typically contain package lists
    PACKAGE_LIST_VARS = [
        "IMAGE_INSTALL",
        "IMAGE_INSTALL:append",
        "RDEPENDS",
        "DEPENDS",
        "RRECOMMENDS",
        "PACKAGECONFIG",
        "PACKAGES",
        "INSTALL_PKGS",
    ]

    # Pattern to match package list variable assignments (including overrides)
    VAR_PATTERN = re.compile(
        r'^([A-Z_]+(?::[a-z_-]+)*)\s*[\+\?]?=\s*"(.*)$'
    )

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        lines = context.lines
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                i += 1
                continue
            
            match = self.VAR_PATTERN.match(stripped)
            if match:
                var_name = match.group(1)
                var_base = var_name.split(":")[0]
                
                # Check if this is a package list variable
                if var_base in self.PACKAGE_LIST_VARS or any(
                    var_name.startswith(v) for v in self.PACKAGE_LIST_VARS
                ):
                    # Check if it's a multi-line assignment
                    if stripped.endswith("\\"):
                        check_results = self._check_multiline_package_list(
                            context, i, var_name, lines
                        )
                        results.extend(check_results)
            
            i += 1
        
        return results

    def _check_multiline_package_list(
        self, context: FileContext, start_line: int, var_name: str, lines: List[str]
    ) -> List[LintResult]:
        """Check a multi-line package list for formatting issues."""
        results = []
        line_num = start_line + 1  # Convert to 1-based
        
        first_line = lines[start_line].strip()
        
        # Rule 1: First line should have no packages (just var = " \)
        # Extract content after the opening quote
        quote_pos = first_line.find('"')
        if quote_pos != -1:
            after_quote = first_line[quote_pos + 1:].rstrip("\\").strip()
            if after_quote:
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message=f"First line of '{var_name}' should not contain packages",
                    context=first_line[:80],
                    hint='Use format: VAR = " \\ (packages start on next line)',
                ))
        
        # Collect all packages from continuation lines
        packages = []
        current_line = start_line + 1
        closing_line = None
        
        while current_line < len(lines):
            line = lines[current_line]
            stripped = line.strip()
            
            # Check for closing quote
            if '"' in stripped:
                closing_line = current_line
                # Check if there are packages on the closing line
                before_quote = stripped.split('"')[0].rstrip("\\").strip()
                if before_quote:
                    results.append(self.create_result(
                        file=context.path,
                        line=current_line + 1,
                        message=f"Closing line of '{var_name}' should not contain packages",
                        context=stripped[:80],
                        hint='Use format: " (only closing quote on last line)',
                    ))
                break
            
            # Extract package name (remove trailing backslash)
            pkg = stripped.rstrip("\\").strip()
            if pkg:
                packages.append((pkg, current_line + 1))
            
            current_line += 1
        
        # Rule 2: Check alphabetical order (if more than one package)
        if len(packages) > 1:
            pkg_names = [p[0].lower() for p in packages]
            sorted_names = sorted(pkg_names)
            
            if pkg_names != sorted_names:
                # Find first out-of-order package
                for idx, (name, sorted_name) in enumerate(zip(pkg_names, sorted_names)):
                    if name != sorted_name:
                        pkg_name, pkg_line = packages[idx]
                        results.append(self.create_result(
                            file=context.path,
                            line=pkg_line,
                            message=f"Packages in '{var_name}' are not in alphabetical order",
                            context=f"'{pkg_name}' should come after previous packages alphabetically",
                            hint="Sort packages alphabetically for consistency",
                        ))
                        break
        
        # Rule 3: Check for blank line after closing quote
        if closing_line is not None:
            next_line_idx = closing_line + 1
            if next_line_idx < len(lines):
                next_line = lines[next_line_idx]
                # Check if next line is non-empty (not blank)
                if next_line.strip():
                    results.append(self.create_result(
                        file=context.path,
                        line=closing_line + 1,
                        message=f"Missing blank line after '{var_name}' closing quote",
                        hint="Add a blank line after the closing quote for readability",
                    ))
        
        return results


class SystemdAutoEnableRule(BaseRule):
    """
    Check that SYSTEMD_AUTO_ENABLE has the :${PN} suffix.
    
    The correct syntax is SYSTEMD_AUTO_ENABLE:${PN} = "enable"
    not just SYSTEMD_AUTO_ENABLE = "enable".
    """
    
    rule_id = "STYLE008"
    name = "SYSTEMD_AUTO_ENABLE Package Suffix"
    description = "Check that SYSTEMD_AUTO_ENABLE uses :${PN} suffix"
    default_severity = Severity.WARNING
    groups = ["style", "systemd"]
    hint = "Use SYSTEMD_AUTO_ENABLE:${PN} instead of SYSTEMD_AUTO_ENABLE"

    # Pattern to match SYSTEMD_AUTO_ENABLE without :${PN}
    PATTERN = re.compile(r'^SYSTEMD_AUTO_ENABLE\s*[+?]?=')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            # Check for SYSTEMD_AUTO_ENABLE without package suffix
            if self.PATTERN.match(stripped):
                # Make sure it's not already using :${PN} or similar
                if not re.match(r'^SYSTEMD_AUTO_ENABLE:[^\s=]+', stripped):
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message="SYSTEMD_AUTO_ENABLE should have :${PN} suffix",
                        context=stripped[:60],
                        hint="Change to SYSTEMD_AUTO_ENABLE:${PN} = ...",
                    ))
        
        return results


class InstallDirectoryTrailingSlashRule(BaseRule):
    """
    Check that install commands use trailing slash for directory destinations.
    
    When installing files to a directory, using a trailing slash is good practice:
    - Makes the destination type (directory) explicit
    - Fails clearly if the directory doesn't exist
    
    Good:  install -m 0644 file.conf ${D}${sysconfdir}/
    Bad:   install -m 0644 file.conf ${D}${sysconfdir}
    """
    
    rule_id = "STYLE009"
    name = "Install Directory Trailing Slash"
    description = "Check install commands use trailing slash for directories"
    default_severity = Severity.INFO
    groups = ["style", "install"]
    hint = "Add trailing / to directory destination in install command"

    # Common directory variable suffixes that indicate a directory destination
    DIRECTORY_VARS = [
        'systemd_system_unitdir',
        'systemd_user_unitdir',
        'sysconfdir',
        'bindir',
        'sbindir',
        'libdir',
        'includedir',
        'datadir',
        'mandir',
        'docdir',
        'infodir',
        'localstatedir',
        'base_bindir',
        'base_sbindir',
        'base_libdir',
        'servicedir',
        'systemd_unitdir',
    ]

    # Pattern to match install commands
    INSTALL_PATTERN = re.compile(
        r'install\s+(?:-[a-zA-Z]+\s+)*(?:-m\s+\d+\s+)?'  # install with options
        r'[^\s]+\s+'  # source file
        r'\$\{D\}\$\{([a-z_]+)\}'  # destination ${D}${var}
        r'(?!/)'  # NOT followed by /
        r'\s*$'  # end of line (or just whitespace)
    )

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            # Look for install commands
            if "install " in stripped and "${D}" in stripped:
                match = self.INSTALL_PATTERN.search(stripped)
                if match:
                    dir_var = match.group(1)
                    if dir_var in self.DIRECTORY_VARS:
                        results.append(self.create_result(
                            file=context.path,
                            line=line_num,
                            message=f"Install to directory ${{{dir_var}}} should end with /",
                            context=stripped[:70],
                            hint=f"Change to ${{D}}${{{dir_var}}}/ (add trailing slash)",
                        ))
        
        return results


class SystemdRedundantFilesRule(BaseRule):
    """
    Check for redundant FILES entries when using systemd class.
    
    The systemd bbclass automatically adds service files to the package,
    service files installed to non-standard locations may not be packaged.
    
    The systemd class auto-adds files from ${systemd_system_unitdir}, but
    service files installed elsewhere need explicit FILES:${PN} entries.
    """
    
    rule_id = "STYLE010"
    name = "Service Files Not in FILES"
    description = "Check for systemd service files installed but not in FILES"
    default_severity = Severity.WARNING
    groups = ["style", "systemd", "packaging"]
    hint = "Add service file path to FILES:${PN}"

    # Pattern to find service file installations in do_install
    SERVICE_INSTALL_PATTERN = re.compile(
        r'install\s+.*?(\S+\.service)\s+.*?\$\{D\}(/\S+)',
        re.IGNORECASE
    )
    
    # Standard systemd directories (auto-handled by systemd class)
    STANDARD_SYSTEMD_DIRS = [
        '${systemd_system_unitdir}',
        '${systemd_user_unitdir}',
        '${systemd_unitdir}',
        '/lib/systemd/system',
        '/usr/lib/systemd/system',
        '/etc/systemd/system',
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Track whether we're inside do_install
        in_do_install = False
        brace_depth = 0
        
        # Collect service file installations to non-standard paths
        service_installs = []  # List of (line_num, service_name, install_path)
        
        # Collect FILES entries
        files_entries = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            # Track do_install function
            if re.match(r'do_install\s*\(', stripped) or \
               re.match(r'do_install:append\s*\(', stripped) or \
               re.match(r'do_install_append\s*\(', stripped):
                in_do_install = True
                brace_depth = 0
            
            if in_do_install:
                brace_depth += stripped.count('{') - stripped.count('}')
                if brace_depth <= 0 and '{' not in stripped and '}' in stripped:
                    in_do_install = False
                
                # Look for service file installations
                match = self.SERVICE_INSTALL_PATTERN.search(line)
                if match:
                    service_name = match.group(1)
                    install_path = match.group(2)
                    
                    # Check if it's a non-standard location
                    is_standard = False
                    for std_dir in self.STANDARD_SYSTEMD_DIRS:
                        if std_dir in line or install_path.startswith(std_dir.replace('${', '').replace('}', '')):
                            is_standard = True
                            break
                    
                    if not is_standard:
                        service_installs.append((line_num, service_name, install_path))
            
            # Collect FILES entries
            if re.match(r'FILES[_:]\$\{PN\}', stripped):
                files_entries.append(stripped)
        
        # Check if service installs are covered by FILES
        for line_num, service_name, install_path in service_installs:
            # Check if this path is covered by any FILES entry
            path_covered = False
            for files_entry in files_entries:
                # Check if the install path or service name appears in FILES
                if install_path in files_entry or service_name in files_entry:
                    path_covered = True
                    break
                # Check for wildcard patterns
                if '*.service' in files_entry:
                    # Check if the directory is covered
                    dir_path = '/'.join(install_path.split('/')[:-1])
                    if dir_path in files_entry:
                        path_covered = True
                        break
            
            if not path_covered:
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message=f"Service file '{service_name}' installed to non-standard location may not be packaged",
                    context=f"Installed to: {install_path}",
                    hint=f"Add 'FILES:${{PN}} += \"{install_path}\"' to ensure the service is packaged",
                ))
        
        return results
