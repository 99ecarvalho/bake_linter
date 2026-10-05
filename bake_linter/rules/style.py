# -*- coding: utf-8 -*-
"""
Code quality and style rules for Yocto recipes.

These rules check for general code quality issues and style violations.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from __future__ import annotations

import fnmatch
import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule
from bake_linter.rules.syntax import InvalidOverrideOrderingRule


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
                    file=context,
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
                    file=context,
                    line=line_num,
                    message=f"Line exceeds {max_length} characters ({len(line.rstrip())} chars)",
                ))
        
        return results


def _strip_inline_python(text: str) -> str:
    """*text* with every inline python expression ${@...} removed, braces
    matched (${@d.getVar('X') or '{}'} is removed whole)."""
    out = []
    depth = 0
    i = 0
    while i < len(text):
        if depth == 0 and text.startswith("${@", i):
            depth = 1
            out.append(" ")
            i += 3
            continue
        char = text[i]
        if depth:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
        else:
            out.append(char)
        i += 1
    return "".join(out)


# Where STYLE003 accepts a hardcoded path: where a path can start (start of
# a word, a quoted string or an assignment) or right after the destination
# root (${D}/etc). This leaves out ${PV}/etc/, file://etc/... and
# -I/usr/include.
_PATH_START = (
    r'(?:(?<=^)|(?<=[\s"\'=(,;])|(?<=\$D)|(?<=\$\{D\})'
    r'|(?<=\$\{PKGD\})|(?<=\$\{IMAGE_ROOTFS\}))'
)
# ...and only as a whole component: not /etc.conf, not /usr/lib for /usr/lib64
_PATH_END = r'(?![\w.-])'


class HardcodedPathsRule(BaseRule):
    """
    Check for hardcoded paths that should use variables.
    
    IMPORTANT: This rule skips documentation variables (SUMMARY, DESCRIPTION, etc.)
    where literal paths like /etc/hosts are appropriate for human readability.
    Users reading package descriptions need to see actual paths, not variables.
    
    Also skips shebang patterns (#!/usr/bin/env, #!/bin/sh, etc.) since these
    are standard Unix runtime conventions, not build-time paths.
    
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

    # Comprehensive mapping of hardcoded paths to BitBake variables
    # Order matters: more specific paths should come first
    # Format: (regex_pattern, variable_name, example_path)
    PATH_MAPPINGS = [
        (re.compile(_PATH_START + re.escape(path) + _PATH_END), var, path)
        for path, var in [
            # /usr/share subdirectories (must come before /usr/share)
            ('/usr/share/man', '${mandir}'),
            ('/usr/share/doc', '${docdir}'),
            # /usr subdirectories
            ('/usr/libexec', '${libexecdir}'),
            ('/usr/include', '${includedir}'),
            ('/usr/share', '${datadir}'),
            ('/usr/sbin', '${sbindir}'),
            ('/usr/bin', '${bindir}'),
            ('/usr/lib64', '${libdir}'),
            ('/usr/lib', '${libdir}'),
            # /var subdirectories (must come before /var)
            ('/var/lib', '${sharedstatedir}'),
            # Root level directories
            ('/etc', '${sysconfdir}'),
            ('/var', '${localstatedir}'),
            ('/srv', '${servicedir}'),
        ]
    ]

    # The search side of a sed s<d>pattern<d>replacement<d> expression: it
    # matches text in the files being edited, so it has to spell paths out.
    SED_EXPRESSION = re.compile(r'\bs([:#,!|@%;/])(.*?)\1')

    # Documentation variables where literal paths are appropriate
    # These describe what software does, not how to build it
    DOCUMENTATION_VARS = [
        'SUMMARY', 'DESCRIPTION', 'HOMEPAGE', 'BUGTRACKER',
        'AUTHOR', 'MAINTAINER', 'SECTION', 'CVE_PRODUCT',
    ]
    
    # Pattern to detect documentation variable assignment
    DOC_VAR_PATTERN = re.compile(r'^(' + '|'.join(DOCUMENTATION_VARS) + r')\s*[+:]?=')
    
    # Shebang patterns - these are standard Unix runtime conventions, not build paths
    # e.g., #!/usr/bin/env python3, #!/bin/sh, #!/bin/bash
    SHEBANG_PATTERNS = [
        re.compile(r'#!/usr/bin/env\b'),      # Portable shebang: #!/usr/bin/env python3
        re.compile(r'#!/bin/sh\b'),           # Standard sh
        re.compile(r'#!/bin/bash\b'),         # Bash
        re.compile(r'#!\s*/usr/bin/'),        # Direct interpreter: #!/usr/bin/python3
        re.compile(r'#!\s*/bin/'),            # Direct interpreter: #!/bin/sh
        re.compile(r"'#!/"),                  # Quoted shebang in string
        re.compile(r'"#!/'),                  # Quoted shebang in string
        re.compile(r'\|#!/'),                 # Shebang in sed/awk pattern
    ]

    def _is_shebang_context(self, line: str) -> bool:
        """Check if the line contains a shebang pattern (runtime convention)."""
        for pattern in self.SHEBANG_PATTERNS:
            if pattern.search(line):
                return True
        return False

    @staticmethod
    def _is_python(context: FileContext, line_num: int, line: str) -> bool:
        """Python code: a python function or def body, or inline ${@...}.
        It runs on the build host and reads host paths (os.path.exists of
        /usr/include/...), which the target directory variables do not
        describe."""
        if "${@" in line:
            return True
        function = context.function_at(line_num)
        return function is not None and function.python

    def _find_path(self, line: str):
        """First hardcoded path on *line* outside sed search patterns, as
        (match, variable, example path), or None."""
        # /usr/bin/env is how scripts find an interpreter at run time
        text = line.replace("/usr/bin/env", "")
        sed_spans = [m.span(2) for m in self.SED_EXPRESSION.finditer(text)]
        for pattern, var_name, example_path in self.PATH_MAPPINGS:
            for match in pattern.finditer(text):
                if any(start <= match.start() < end for start, end in sed_spans):
                    continue
                return match, var_name, example_path
        return None

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()

            # Skip comments
            if stripped.startswith("#"):
                continue

            # Skip SRC_URI lines (URLs legitimately contain paths)
            if "SRC_URI" in line or context.owner_base(line_num) == "SRC_URI":
                continue

            # Skip documentation variables (SUMMARY, DESCRIPTION, etc.),
            # continuation lines included. Literal paths are appropriate
            # for human-readable documentation.
            assignment = context.assignment_at(line_num)
            if assignment is not None and assignment.base in self.DOCUMENTATION_VARS:
                continue
            if self.DOC_VAR_PATTERN.match(stripped):
                continue

            # Skip shebang patterns - these are runtime conventions, not build paths
            # e.g., #!/usr/bin/env python3 is the standard portable shebang
            if self._is_shebang_context(line):
                continue

            if self._is_python(context, line_num, line):
                continue

            found = self._find_path(line)
            if found:
                match, var_name, example_path = found
                # Generate helpful suggestion showing the replacement
                matched_path = match.group(0)
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message=f"Hardcoded path '{matched_path}' should use {var_name}",
                    context=stripped[:60],
                    hint=f"Replace '{matched_path}' with '{var_name}' (e.g., {var_name}/myfile instead of {example_path}/myfile)",
                ))

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
                    file=context,
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

    @staticmethod
    def _is_override_scoped(context: FileContext, line_num: int) -> bool:
        """Whether the assignment on *line_num* carries an override.

        Read from the source line so this does not depend on how the parser
        keys an overridden name.
        """
        if not line_num or line_num > len(context.lines):
            return False
        stripped = context.lines[line_num - 1].strip()
        name_part = stripped.split('=', 1)[0]
        return ':' in name_part

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        for var_name, assignments in context.variables.items():
            for assignment in assignments:
                if not assignment.value.strip() and assignment.operator == "=":
                    # Skip known intentionally empty variables
                    if var_name in {"SRC_URI", "DEPENDS", "RDEPENDS"}:
                        continue

                    # Blanking a variable under an override is the deliberate
                    # way to exclude something for one machine/distro/class:
                    # VAR:qemuarm64 = "" drops it there and nowhere else, a
                    # common idiom in oe-core and meta-openembedded.
                    if self._is_override_scoped(context, assignment.line):
                        continue

                    results.append(self.create_result(
                        file=context,
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
                # A conditional ${@...} is one expression, not a list of
                # classes: its quoted arguments are not inherits.
                classes = _strip_inline_python(stripped).split()[1:]
                for cls in classes:
                    if cls in seen_classes:
                        results.append(self.create_result(
                            file=context,
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

    # Lists whose order means something, so it is not checked: the first
    # package in PACKAGES whose FILES match a file gets it.
    ORDERED_VARS = {"PACKAGES"}

    # Pattern to match package list variable assignments (including overrides)
    VAR_PATTERN = re.compile(
        r'^([A-Z_]+(?::[a-z_-]+)*)\s*[\+\?]?=\s*"(.*)$'
    )

    @staticmethod
    def _closing_quote(text: str) -> int:
        """Index of the first double quote in *text* that is not inside an
        inline python expression ${@...}, or -1."""
        depth = 0
        i = 0
        while i < len(text):
            if text.startswith("${@", i) and depth == 0:
                depth = 1
                i += 3
                continue
            char = text[i]
            if depth:
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
            elif char == '"':
                return i
            i += 1
        return -1

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

                # Check if this is a package list variable (by its exact
                # name: PACKAGECONFIG_GL or PACKAGES_DYNAMIC are not lists
                # of packages)
                if var_base in self.PACKAGE_LIST_VARS:
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
                    file=context,
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
            
            # Check for closing quote (quotes inside ${@...} do not close)
            quote = self._closing_quote(stripped)
            if quote != -1:
                closing_line = current_line
                # Check if there are packages on the closing line
                before_quote = stripped[:quote].rstrip("\\").strip()
                if before_quote:
                    results.append(self.create_result(
                        file=context,
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
        
        # Rule 2: Check alphabetical order (if more than one package).
        # Entries that are expansions (${VIRTUAL-RUNTIME_x}, ${@...}) have
        # no name to sort by, and some lists are ordered on purpose.
        packages = [p for p in packages if not p[0].startswith("${")]
        if var_name.split(":")[0] in self.ORDERED_VARS:
            packages = []
        if len(packages) > 1:
            pkg_names = [p[0].lower() for p in packages]
            sorted_names = sorted(pkg_names)
            
            if pkg_names != sorted_names:
                # Find first out-of-order package
                for idx, (name, sorted_name) in enumerate(zip(pkg_names, sorted_names)):
                    if name != sorted_name:
                        pkg_name, pkg_line = packages[idx]
                        results.append(self.create_result(
                            file=context,
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
                        file=context,
                        line=closing_line + 1,
                        message=f"Missing blank line after '{var_name}' closing quote",
                        hint="Add a blank line after the closing quote for readability",
                    ))
        
        return results


class SystemdAutoEnableRule(BaseRule):
    """
    Check that SYSTEMD_AUTO_ENABLE names its package when it is ambiguous.

    An unsuffixed SYSTEMD_AUTO_ENABLE is NOT an error. systemd.bbclass reads it
    through get_package_var, which falls back to the unsuffixed variable when no
    per-package one is set:

        def get_package_var(d, var, pkg):
            val = (d.getVar('%s:%s' % (var, pkg)) or "").strip()
            if val == "":
                val = (d.getVar(var) or "").strip()
            return val

    So the bare form works, and it is the dominant idiom: poky itself uses it in
    seven recipes against one that suffixes it.

    It becomes ambiguous only when a recipe ships systemd services in more than
    one package, because then one bare value silently applies to all of them,
    which is rarely what the author meant. That is the only case this rule
    reports.
    """

    rule_id = "STYLE008"
    name = "SYSTEMD_AUTO_ENABLE Package Suffix"
    description = "Check that SYSTEMD_AUTO_ENABLE names its package when the recipe has more than one systemd package"
    default_severity = Severity.WARNING
    groups = ["style", "systemd"]
    hint = "Use SYSTEMD_AUTO_ENABLE:<pkg> when more than one package ships services"

    # Pattern to match SYSTEMD_AUTO_ENABLE without a package suffix
    PATTERN = re.compile(r'^SYSTEMD_AUTO_ENABLE\s*[+?:]?=')

    # The package a SYSTEMD_SERVICE assignment targets: the token right after
    # the first colon, stopping before any further override (:append, :qemuarm).
    SERVICE_PKG_PATTERN = re.compile(
        r'^SYSTEMD_SERVICE:((?:\$\{[A-Za-z_][A-Za-z0-9_]*\}|[A-Za-z0-9_.+-])+)'
    )

    # The packages systemd.bbclass processes, listed in SYSTEMD_PACKAGES
    PACKAGES_PATTERN = re.compile(
        r'^SYSTEMD_PACKAGES(?::(?:append|prepend))?\s*(?:\?\?|\?|\+|:|\.)?=\+?\s*"([^"]*)"'
    )

    OPERATIONS = {"append", "prepend", "remove"}

    def _systemd_packages(self, context: FileContext) -> set:
        """Distinct packages this recipe declares systemd services for."""
        conditional = InvalidOverrideOrderingRule.CONDITIONAL_OVERRIDE_PATTERN

        def resolve(package: str) -> str:
            # ${PN} and foo name the same package in foo_1.0.bb
            return package.replace("${PN}", context.pn).replace("${BPN}", context.pn)

        packages = set()
        for line in context.lines:
            stripped = line.strip()
            match = self.SERVICE_PKG_PATTERN.match(stripped)
            if match:
                package = match.group(1)
                # SYSTEMD_SERVICE:append or SYSTEMD_SERVICE:class-target name
                # no package: they change the unsuffixed value.
                if package not in self.OPERATIONS and not conditional.match(package):
                    packages.add(resolve(package))
            match = self.PACKAGES_PATTERN.match(stripped)
            if match:
                packages.update(resolve(p) for p in match.group(1).split())
        return packages

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        # One package, or none declared here, means the bare form is
        # unambiguous and correct. Reporting it would contradict both
        # systemd.bbclass and upstream convention.
        if len(self._systemd_packages(context)) < 2:
            return results

        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()

            # Skip comments
            if stripped.startswith("#"):
                continue

            if self.PATTERN.match(stripped):
                # Already package-qualified: nothing to say.
                if not re.match(r'^SYSTEMD_AUTO_ENABLE:[^\s=]+', stripped):
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message="SYSTEMD_AUTO_ENABLE applies to every systemd package in this recipe",
                        context=stripped[:60],
                        hint="Name the package: SYSTEMD_AUTO_ENABLE:<pkg> = ...",
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
                            file=context,
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

    @staticmethod
    def _covered_by_files(install_path: str, service_name: str, tokens: List[str]) -> bool:
        """Whether a FILES glob packages the service installed at
        *install_path* (a directory, or the file itself). FILES entries are
        globs, and a matched directory is packaged with its contents."""
        # ${D}/${datadir}/x is ${D}${datadir}/x: the slash is redundant
        path = re.sub(r'^/+(?=\$\{)', '', install_path).rstrip('/')
        candidates = {path, f"{path}/{service_name.rsplit('/', 1)[-1]}"}
        for token in tokens:
            token = token.rstrip('/')
            for candidate in candidates:
                if fnmatch.fnmatchcase(candidate, token):
                    return True
                if candidate.startswith(token + '/'):
                    return True
        return False

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

        # FILES values as package.bbclass reads them: whole logical
        # assignments (continuation lines included), one glob per token
        files_tokens = []
        for assignment in context.structure.assignments:
            if assignment.base == "FILES" or assignment.name.startswith("FILES_${PN}"):
                files_tokens.extend(assignment.value.split())

        # Check if service installs are covered by FILES
        for line_num, service_name, install_path in service_installs:
            # Check if this path is covered by any FILES entry
            path_covered = self._covered_by_files(install_path, service_name, files_tokens)
            for files_entry in files_entries:
                if path_covered:
                    break
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
                    file=context,
                    line=line_num,
                    message=f"Service file '{service_name}' installed to non-standard location may not be packaged",
                    context=f"Installed to: {install_path}",
                    hint=f"Add 'FILES:${{PN}} += \"{install_path}\"' to ensure the service is packaged",
                ))
        
        return results

class HardcodedSystemdPathInFilesRule(BaseRule):
    """
    Check for hardcoded systemd paths in FILES variable.
    
    While hardcoded paths in FILES work correctly (they describe actual runtime
    target filesystem paths), using variables like ${systemd_system_unitdir}
    is preferred for:
    - Consistency with do_install patterns
    - Portability across different distributions
    - Better maintainability
    
    This is a STYLE issue (INFO level), not an error. The code functions
    correctly either way.
    """
    
    rule_id = "STYLE011"
    name = "Hardcoded Systemd Paths in FILES"
    description = "Suggests using systemd variables in FILES for consistency"
    default_severity = Severity.INFO
    groups = ["style", "systemd", "portability"]

    # Hardcoded paths and their variable replacements
    HARDCODED_PATHS = [
        (re.compile(r'/lib/systemd/system(?![a-z])'), "${systemd_system_unitdir}"),
        (re.compile(r'/usr/lib/systemd/system(?![a-z])'), "${systemd_system_unitdir}"),
        (re.compile(r'/etc/systemd/system(?![a-z])'), "${sysconfdir}/systemd/system"),
        (re.compile(r'/lib/systemd/user(?![a-z])'), "${systemd_user_unitdir}"),
        (re.compile(r'/usr/lib/systemd/user(?![a-z])'), "${systemd_user_unitdir}"),
        (re.compile(r'/lib/systemd(?![a-z/])'), "${systemd_unitdir}"),
        (re.compile(r'/usr/lib/systemd(?![a-z/])'), "${systemd_unitdir}"),
    ]

    # Patterns to detect FILES variable contexts
    FILES_START_PATTERN = re.compile(r'^\s*FILES[_:]')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Track if we're inside a multi-line FILES variable
        in_files_var = False
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            # Track FILES variable blocks
            if self.FILES_START_PATTERN.match(line):
                in_files_var = True
            
            if in_files_var:
                # Check for hardcoded paths
                for pattern, replacement in self.HARDCODED_PATHS:
                    if pattern.search(line):
                        results.append(self.create_result(
                            file=context,
                            line=line_num,
                            message="Hardcoded systemd path in FILES variable",
                            context=stripped[:70],
                            hint=f"Consider using {replacement} for consistency with do_install",
                        ))
                        break  # One info per line
                
                # End of FILES block when line ends with closing quote
                if not stripped.endswith('\\') and (stripped.endswith('"') or stripped.endswith("'")):
                    in_files_var = False
        
        return results


class VariableAssignmentSpacingRule(BaseRule):
    """
    Check for proper spacing around assignment operators in BitBake variables.
    
    BitBake style guide recommends spaces around assignment operators:
    - GOOD: FOO = "bar"
    - BAD:  FOO="bar"
    
    This applies to all assignment operators: =, +=, =+, :=, ?=, ??=
    
    Context-aware: Skips shell function bodies and Python function bodies.
    """
    
    rule_id = "STYLE012"
    name = "Variable Assignment Spacing"
    description = "Check for proper spacing around assignment operators"
    default_severity = Severity.INFO
    groups = ["style", "formatting"]
    hint = "Add spaces around the assignment operator"

    # Pattern to match BitBake variable assignments
    # Captures: variable name, operator, optional space, rest of line
    # This pattern detects MISSING spaces around operators
    ASSIGNMENT_NO_SPACE_PATTERN = re.compile(
        r'^([A-Z][A-Z0-9_]*(?::[a-z0-9_${}-]+)*)'  # Variable name with optional overrides
        r'(\?\?=|\?=|:=|\+=|=\+|\.=|=\.|=)'  # Assignment operator
        r'(?!\s)',                                  # NOT followed by space (captures missing space after)
    )
    
    # Pattern to detect missing space BEFORE operator
    MISSING_SPACE_BEFORE_PATTERN = re.compile(
        r'^([A-Z][A-Z0-9_]*(?::[a-z0-9_${}-]+)*)'  # Variable name with optional overrides
        r'(?<!\s)'                                  # No space before
        r'(\?\?=|\?=|:=|\+=|=\+|\.=|=\.|=)'  # Assignment operator
    )
    
    # Full pattern to check for proper spacing (space before and after operator)
    PROPER_SPACING_PATTERN = re.compile(
        r'^([A-Z][A-Z0-9_]*(?::[a-z0-9_${}-]+)*)'  # Variable name with optional overrides
        r'\s+'                                      # Space(s) before operator
        r'(\?\?=|\?=|:=|\+=|=\+|\.=|=\.|=)'  # Assignment operator  
        r'\s+',                                     # Space(s) after operator
    )
    
    # Pattern for variable assignment without proper spacing
    BAD_SPACING_PATTERN = re.compile(
        r'^([A-Z][A-Z0-9_]*(?::[a-z0-9_${}-]+)*)'  # Variable name
        r'(\s*)'                                    # Optional space before operator
        r'(\?\?=|\?=|:=|\+=|=\+|\.=|=\.|=)'  # Operator
        r'(\s*)'                                    # Optional space after operator
        r'(.*)$'                                    # Rest of line
    )
    
    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue
            
            # Only the first line of a BitBake assignment: function bodies
            # (whatever their header) and continuation lines hold shell or
            # python code and values, not assignments.
            if not context.is_top_level_assignment(line_num):
                continue
            
            # Skip require/include statements
            if stripped.startswith(("require", "include", "inherit")):
                continue
            
            # Check for variable assignment with improper spacing
            match = self.BAD_SPACING_PATTERN.match(stripped)
            if match:
                var_name = match.group(1)
                space_before = match.group(2)
                operator = match.group(3)
                space_after = match.group(4)
                
                # Check if spacing is correct (should have space before and after)
                has_space_before = len(space_before) > 0
                has_space_after = len(space_after) > 0
                
                if not has_space_before or not has_space_after:
                    issues = []
                    if not has_space_before:
                        issues.append("before")
                    if not has_space_after:
                        issues.append("after")
                    
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message=f"Missing space {' and '.join(issues)} '{operator}' operator in assignment",
                        context=stripped[:60],
                        hint=f"Use: {var_name} {operator} \"...\" (with spaces around {operator})",
                    ))
        
        return results


class SingleQuoteUsageRule(BaseRule):
    """
    Check for single quote usage in BitBake variable assignments.
    
    BitBake style guide recommends double quotes for variable assignments:
    - GOOD: FOO = "bar"
    - BAD:  FOO = 'bar'
    
    Single quotes are acceptable in shell code within tasks.
    
    Context-aware: Skips shell function bodies and Python function bodies.
    """
    
    rule_id = "STYLE013"
    name = "Single Quote Usage"
    description = "Check for single quotes in variable assignments (should use double quotes)"
    default_severity = Severity.INFO
    groups = ["style", "formatting"]
    hint = "Use double quotes for BitBake variable assignments"

    # Pattern to detect BitBake variable assignment with single quotes
    SINGLE_QUOTE_ASSIGNMENT = re.compile(
        r"^([A-Z][A-Z0-9_]*(?::[a-z0-9_${}-]+)*)"  # Variable name with optional overrides
        r"\s*"                                      # Optional space
        r"(\?\?=|\?=|:=|\+=|=\+|\.=|=\.|=)"  # Assignment operator
        r"\s*"                                      # Optional space
        r"'([^']*)'"                               # Single-quoted value
        r"\s*$"                                     # End of line (simple single-line case)
    )
    
    # Simpler pattern: variable assignment followed by single quote
    VAR_WITH_SINGLE_QUOTE = re.compile(
        r"^([A-Z][A-Z0-9_]*(?::[a-z0-9_${}-]+)*)"  # Variable name
        r"\s*"                                      # Optional space
        r"(\?\?=|\?=|:=|\+=|=\+|\.=|=\.|=)"  # Assignment operator
        r"\s*"                                      # Optional space
        r"'"                                        # Single quote
    )
    
    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue
            
            # Only the first line of a BitBake assignment: function bodies
            # (whatever their header) and continuation lines hold shell or
            # python code and values, not assignments.
            if not context.is_top_level_assignment(line_num):
                continue
            
            # Skip require/include statements
            if stripped.startswith(("require", "include", "inherit")):
                continue
            
            # Check for variable assignment with single quotes
            if self.VAR_WITH_SINGLE_QUOTE.match(stripped):
                match = self.VAR_WITH_SINGLE_QUOTE.match(stripped)
                var_name = match.group(1)
                operator = match.group(2)

                # A value that contains double quotes (shell or make
                # arguments such as KERNEL_DIR="${STAGING_KERNEL_DIR}") is
                # single quoted on purpose
                assignment = context.assignment_at(line_num)
                if assignment is not None and '"' in assignment.value:
                    continue

                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message=f"Single quotes used in '{var_name}' assignment",
                    context=stripped[:60],
                    hint=f"Use double quotes: {var_name} {operator} \"...\"",
                ))
        
        return results


class TabInVariableDefinitionRule(BaseRule):
    """
    Check for tab characters in variable definitions.
    
    BitBake style guide recommends using spaces (typically 4) for indentation:
    - GOOD: FOO = "value \\
                continuation"
    - BAD:  FOO = "value \\
    	continuation"  (tab used)
    
    Tabs can cause parsing issues and inconsistent display.
    """
    
    rule_id = "STYLE014"
    name = "Tab in Variable Definition"
    description = "Check for tab characters in variable definitions (should use spaces)"
    default_severity = Severity.WARNING
    groups = ["style", "formatting"]
    hint = "Replace tabs with 4 spaces per indentation level"

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()

            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue

            # Only lines of a BitBake variable assignment (its first line
            # and continuation lines). Function bodies, under any header
            # (do_install:append:class-native(), pkg_postinst:${PN} (),
            # fakeroot f()), are shell or python code where tabs are fine.
            assignment = context.assignment_at(line_num)
            if assignment is None or not assignment.name[:1].isupper():
                continue

            # Check for tabs in variable assignments or continuations
            if '\t' in line:
                # Count tabs for reporting
                tab_count = line.count('\t')
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message=f"Tab character(s) found in variable definition ({tab_count} tab{'s' if tab_count > 1 else ''})",
                    context=stripped[:60],
                    hint="Replace tabs with 4 spaces per indentation level",
                ))

        return results


class MultilineContinuationAlignmentRule(BaseRule):
    """
    Check for proper alignment of continuation lines in multiline variable assignments.
    
    Continuation lines should be consistently indented. Common patterns:
    
    1. Aligned with opening quote:
       FOO = "this is \\
             continuation"
    
    2. Consistent indentation from variable name (4 spaces):
       SRC_URI = "\\
           file://patch1.patch \\
           file://patch2.patch \\
       "
    
    The key is consistency within a single variable assignment.
    """
    
    rule_id = "STYLE015"
    name = "Multiline Continuation Alignment"
    description = "Check alignment of continuation lines in multiline variable assignments"
    default_severity = Severity.INFO
    groups = ["style", "formatting"]
    hint = "Align continuation lines consistently"

    # Pattern to detect BitBake variable assignment start
    VAR_ASSIGNMENT_START = re.compile(
        r'^(\s*)([A-Z][A-Z0-9_]*(?::[a-z0-9_${}-]+)*)\s*(\?\?=|\?=|:=|\+=|=\+|\.=|=\.|=)\s*"(.*)'
    )
    
    # Minimum indentation expected for continuation lines (typically 4 spaces)
    MIN_CONTINUATION_INDENT = 4

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Track multiline variable state
        in_multiline_var = False
        var_name = ""
        first_line_num = 0
        expected_indent = 0
        first_continuation_indent = None
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue
            
            # Function bodies are shell or python code, not values
            if context.owner(line_num).startswith("FUNC:"):
                in_multiline_var = False
                continue
            
            # Check if this is a new variable assignment
            # (only a line that starts a logical assignment: a continuation
            # line such as  FOO="bar" \  inside EXTRA_OEMAKE is not one)
            match = (
                self.VAR_ASSIGNMENT_START.match(line)
                if context.is_top_level_assignment(line_num) else None
            )
            if match:
                leading_space = match.group(1)
                var_name = match.group(2)
                operator = match.group(3)
                
                # Check if it's a multiline assignment
                if stripped.rstrip().endswith('\\'):
                    in_multiline_var = True
                    first_line_num = line_num
                    
                    # Calculate expected indentation for continuation
                    # Option 1: Indent from variable name position + MIN_CONTINUATION_INDENT
                    # Option 2: Align with opening quote
                    quote_pos = line.find('"')
                    if quote_pos != -1:
                        expected_indent = quote_pos + 1  # Position after opening quote
                    else:
                        expected_indent = len(leading_space) + self.MIN_CONTINUATION_INDENT
                    
                    first_continuation_indent = None  # Will be set on first continuation
                else:
                    in_multiline_var = False
                    first_continuation_indent = None
                continue
            
            # Check continuation lines
            if in_multiline_var:
                # Calculate actual indentation, a tab moving to the next
                # multiple of 8 as it does on screen
                expanded = line.expandtabs(8)
                actual_indent = len(expanded) - len(expanded.lstrip())
                
                # First continuation line sets the expected pattern
                if first_continuation_indent is None:
                    first_continuation_indent = actual_indent
                    # Check if indent is too small (less than MIN_CONTINUATION_INDENT)
                    if actual_indent < self.MIN_CONTINUATION_INDENT:
                        results.append(self.create_result(
                            file=context,
                            line=line_num,
                            message=f"Continuation line has insufficient indentation ({actual_indent} spaces)",
                            context=stripped[:60],
                            hint=f"Use at least {self.MIN_CONTINUATION_INDENT} spaces for continuation lines",
                        ))
                else:
                    # Subsequent lines should match the first continuation's indentation
                    # Allow closing quote line to have different indentation
                    is_closing_line = stripped == '"' or stripped.rstrip('\\').strip() == '"'
                    
                    if not is_closing_line and actual_indent != first_continuation_indent:
                        results.append(self.create_result(
                            file=context,
                            line=line_num,
                            message=f"Inconsistent continuation indentation ({actual_indent} vs {first_continuation_indent} spaces)",
                            context=stripped[:60],
                            hint=f"Align with previous continuation lines ({first_continuation_indent} spaces)",
                        ))
                
                # Check if multiline ends
                if not stripped.rstrip().endswith('\\'):
                    in_multiline_var = False
                    first_continuation_indent = None
        
        return results


class PythonFunctionIndentationRule(BaseRule):
    """
    Check that Python functions use 4 spaces for indentation.
    
    Per Yocto style guide, Python code must use spaces for indentation,
    with 4 spaces per indentation level. Tabs are not allowed.
    
    This checks:
    - No tab characters in Python function bodies
    - Consistent 4-space indentation increments
    """
    
    rule_id = "STYLE016"
    name = "Python Function Indentation"
    description = "Check Python functions use 4 spaces for indentation"
    default_severity = Severity.WARNING
    groups = ["style", "formatting", "python"]
    hint = "Use 4 spaces per indentation level in Python functions"

    # Patterns to detect Python function contexts
    PYTHON_FUNC_START = re.compile(r'^python\s+([a-z_][a-z0-9_]*)\s*\(\s*\)\s*\{')
    ANON_PYTHON_START = re.compile(r'^python\s*\(\s*\)\s*\{')
    PYTHON_TASK_OVERRIDE = re.compile(r'^python\s+do_[a-z_]+(?::[a-z_]+)*\s*\(\s*\)\s*\{')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_python_func = False
        func_name = ""
        func_start_line = 0
        brace_depth = 0
        base_indent = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip empty lines and comments outside functions
            if not stripped:
                continue
            
            # Check for Python function start
            match = self.PYTHON_FUNC_START.match(stripped)
            if not match:
                match = self.ANON_PYTHON_START.match(stripped)
            if not match:
                match = self.PYTHON_TASK_OVERRIDE.match(stripped)
            
            if match:
                in_python_func = True
                func_name = match.group(1) if match.lastindex else "anonymous"
                func_start_line = line_num
                brace_depth = stripped.count('{') - stripped.count('}')
                # Calculate base indentation from the function definition
                base_indent = len(line) - len(line.lstrip())
                continue
            
            if in_python_func:
                brace_depth += stripped.count('{') - stripped.count('}')
                
                # Check for tabs in Python code
                if '\t' in line:
                    tab_count = line.count('\t')
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message=f"Tab character(s) in Python function '{func_name}' ({tab_count} tab{'s' if tab_count > 1 else ''})",
                        context=stripped[:60],
                        hint="Replace tabs with 4 spaces per indentation level",
                    ))
                
                # Check indentation is multiple of 4 (relative to function body)
                if stripped and not stripped.startswith('#'):
                    current_indent = len(line) - len(line.lstrip())
                    # Indent relative to function start should be multiple of 4
                    relative_indent = current_indent - base_indent
                    if relative_indent > 0 and relative_indent % 4 != 0:
                        # Don't flag continuation lines or closing braces
                        if not stripped.startswith('}') and not line.rstrip().endswith('\\'):
                            results.append(self.create_result(
                                file=context,
                                line=line_num,
                                message=f"Python indentation not multiple of 4 spaces (found {relative_indent} relative spaces)",
                                context=stripped[:60],
                                hint="Use 4 spaces per indentation level",
                            ))
                
                # Exit function when braces balance
                if brace_depth <= 0:
                    in_python_func = False
                    func_name = ""
        
        return results


class RecipeVariableOrderRule(BaseRule):
    """
    Check that recipe variables follow the recommended ordering.
    
    Per Yocto style guide, variables should follow this general order:
    1. SUMMARY, DESCRIPTION, HOMEPAGE, BUGTRACKER, SECTION
    2. LICENSE, LIC_FILES_CHKSUM
    3. DEPENDS, PROVIDES
    4. PV, SRC_URI, SRCREV, S
    5. inherit statements
    6. PACKAGECONFIG
    7. Build class specific variables
    8. Tasks
    9. PACKAGE_ARCH, PACKAGES, FILES
    10. RDEPENDS, RRECOMMENDS, etc.
    11. BBCLASSEXTEND
    
    This rule provides INFO-level suggestions when ordering differs significantly.
    """
    
    rule_id = "STYLE017"
    name = "Recipe Variable Ordering"
    description = "Check recipe variables follow recommended ordering"
    default_severity = Severity.INFO
    groups = ["style", "ordering"]
    hint = "Consider reordering variables per Yocto style guide"
    enabled_by_default = True

    # Define variable categories in recommended order
    # Each category has a priority (lower = earlier in file)
    VARIABLE_ORDER = {
        # Metadata (priority 1-10)
        'SUMMARY': 1,
        'DESCRIPTION': 2,
        'HOMEPAGE': 3,
        'BUGTRACKER': 4,
        'SECTION': 5,
        'AUTHOR': 6,
        
        # License (priority 10-20)
        'LICENSE': 11,
        'LIC_FILES_CHKSUM': 12,
        
        # Dependencies and provides (priority 20-30)
        'DEPENDS': 21,
        'PROVIDES': 22,
        
        # Version and source (priority 30-40)
        'PV': 31,
        'PR': 32,
        'SRC_URI': 33,
        'SRCREV': 34,
        'SRCBRANCH': 35,
        'S': 36,
        'B': 37,
        
        # Build configuration (priority 50-60)
        'PACKAGECONFIG': 51,
        'EXTRA_OECONF': 52,
        'EXTRA_OECMAKE': 53,
        'EXTRA_QMAKEVARS_POST': 54,
        'EXTRA_QMAKEVARS_PRE': 55,
        
        # Packaging (priority 70-80)
        'PACKAGE_ARCH': 71,
        'PACKAGES': 72,
        'FILES': 73,
        
        # Runtime dependencies (priority 80-90)
        'RDEPENDS': 81,
        'RRECOMMENDS': 82,
        'RSUGGESTS': 83,
        'RPROVIDES': 84,
        'RCONFLICTS': 85,
        'RREPLACES': 86,
        
        # Extension (priority 99)
        'BBCLASSEXTEND': 99,
    }
    
    # Pattern to extract variable name from assignment
    VAR_ASSIGNMENT = re.compile(r'^([A-Z][A-Z0-9_]*)(?::[^\s=]+)?\s*[\+\?:]?=')
    
    # Pattern to detect inherit statement
    INHERIT_PATTERN = re.compile(r'^inherit\s+')
    
    # Pattern to detect task definitions
    TASK_PATTERN = re.compile(r'^(do_[a-z_]+)(?::[a-z_]+)?\s*\(')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Collect variable positions
        var_positions = []  # List of (line_num, var_name, priority)
        inherit_line = None
        task_start_line = None
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments and empty lines
            if not stripped or stripped.startswith('#'):
                continue
            
            # Track inherit statement
            if self.INHERIT_PATTERN.match(stripped):
                if inherit_line is None:
                    inherit_line = line_num
                continue
            
            # Track first task
            if self.TASK_PATTERN.match(stripped):
                if task_start_line is None:
                    task_start_line = line_num
                continue
            
            # Extract variable name
            match = self.VAR_ASSIGNMENT.match(stripped)
            if match:
                var_name = match.group(1)
                # Get base variable name (without package suffix)
                base_var = var_name.split(':')[0] if ':' in var_name else var_name
                
                if base_var in self.VARIABLE_ORDER:
                    priority = self.VARIABLE_ORDER[base_var]
                    var_positions.append((line_num, var_name, priority))
        
        # Check for out-of-order variables
        if len(var_positions) >= 2:
            # Check for major ordering issues
            for i in range(len(var_positions) - 1):
                curr_line, curr_var, curr_priority = var_positions[i]
                next_line, next_var, next_priority = var_positions[i + 1]
                
                # Only flag if there's a significant ordering issue
                # (variable from a later category appears before one from an earlier category)
                priority_diff = curr_priority - next_priority
                
                if priority_diff >= 10:  # Significant category difference
                    # Get category names for clarity
                    curr_cat = self._get_category(curr_priority)
                    next_cat = self._get_category(next_priority)
                    
                    results.append(self.create_result(
                        file=context,
                        line=curr_line,
                        message=f"'{curr_var}' ({curr_cat}) appears before '{next_var}' ({next_cat})",
                        context=f"Consider placing {next_var} before {curr_var}",
                        hint=f"Yocto style suggests: metadata → license → source → build → packaging → runtime",
                    ))
        
        # Check if inherit comes after variables that should follow it
        if inherit_line:
            for line_num, var_name, priority in var_positions:
                # Variables with priority >= 50 should come after inherit
                if priority >= 50 and line_num < inherit_line:
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message=f"'{var_name}' typically appears after 'inherit' statement",
                        hint="Move 'inherit' before build configuration and packaging variables",
                    ))
                    break  # One warning is enough
        
        return results
    
    def _get_category(self, priority: int) -> str:
        """Get human-readable category name from priority."""
        if priority <= 10:
            return "metadata"
        elif priority <= 20:
            return "license"
        elif priority <= 30:
            return "dependencies"
        elif priority <= 40:
            return "source"
        elif priority <= 60:
            return "build config"
        elif priority <= 75:
            return "packaging"
        elif priority <= 90:
            return "runtime deps"
        else:
            return "extension"


class LicenseVariablesOrderRule(BaseRule):
    """
    Check that LICENSE comes before LIC_FILES_CHKSUM.
    
    Per Yocto style guide, LICENSE should be defined before LIC_FILES_CHKSUM.
    """
    
    rule_id = "STYLE018"
    name = "LICENSE Variable Order"
    description = "Check LICENSE appears before LIC_FILES_CHKSUM"
    default_severity = Severity.INFO
    groups = ["style", "ordering", "license"]
    hint = "Place LICENSE before LIC_FILES_CHKSUM"

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        license_line = None
        lic_files_line = None
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith('#'):
                continue
            
            if stripped.startswith('LICENSE') and '=' in stripped:
                if license_line is None:
                    license_line = line_num
            
            if stripped.startswith('LIC_FILES_CHKSUM') and '=' in stripped:
                if lic_files_line is None:
                    lic_files_line = line_num
        
        # Check order
        if license_line and lic_files_line:
            if lic_files_line < license_line:
                results.append(self.create_result(
                    file=context,
                    line=lic_files_line,
                    message="LIC_FILES_CHKSUM appears before LICENSE",
                    hint="Place LICENSE before LIC_FILES_CHKSUM per Yocto style guide",
                ))
        
        return results


class SourceVariablesOrderRule(BaseRule):
    """
    Check that source-related variables are in the recommended order.
    
    Recommended order: SRC_URI → SRCREV → S
    """
    
    rule_id = "STYLE019"
    name = "Source Variables Order"
    description = "Check SRC_URI, SRCREV, S are in recommended order"
    default_severity = Severity.INFO
    groups = ["style", "ordering", "source"]
    hint = "Order source variables: SRC_URI → SRCREV → S"

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        src_uri_line = None
        srcrev_line = None
        s_line = None
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith('#'):
                continue
            
            # Match SRC_URI (but not SRC_URI:append etc for simplicity)
            if re.match(r'^SRC_URI\s*[+?:]?=', stripped):
                if src_uri_line is None:
                    src_uri_line = line_num
            
            if re.match(r'^SRCREV\s*[+?:]?=', stripped):
                if srcrev_line is None:
                    srcrev_line = line_num
            
            # Match S but not SECTION, SUMMARY, etc.
            if re.match(r'^S\s*[+?:]?=', stripped):
                if s_line is None:
                    s_line = line_num
        
        # Check SRCREV before SRC_URI
        if src_uri_line and srcrev_line and srcrev_line < src_uri_line:
            results.append(self.create_result(
                file=context,
                line=srcrev_line,
                message="SRCREV appears before SRC_URI",
                hint="Place SRC_URI before SRCREV per Yocto style guide",
            ))
        
        # Check S before SRC_URI
        if src_uri_line and s_line and s_line < src_uri_line:
            results.append(self.create_result(
                file=context,
                line=s_line,
                message="S appears before SRC_URI",
                hint="Place SRC_URI before S per Yocto style guide",
            ))
        
        # Check S before SRCREV (if both exist)
        if srcrev_line and s_line and s_line < srcrev_line:
            results.append(self.create_result(
                file=context,
                line=s_line,
                message="S appears before SRCREV",
                hint="Place SRCREV before S per Yocto style guide",
            ))
        
        return results


class MetadataBeforeLicenseRule(BaseRule):
    """
    Check that metadata variables come before license variables.
    
    SUMMARY, DESCRIPTION, HOMEPAGE, BUGTRACKER should appear before LICENSE.
    """
    
    rule_id = "STYLE020"
    name = "Metadata Before License"
    description = "Check metadata variables appear before LICENSE"
    default_severity = Severity.INFO
    groups = ["style", "ordering", "metadata"]
    hint = "Place SUMMARY, DESCRIPTION, HOMEPAGE before LICENSE"

    METADATA_VARS = ['SUMMARY', 'DESCRIPTION', 'HOMEPAGE', 'BUGTRACKER', 'SECTION']

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        license_line = None
        
        # Find first LICENSE line
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            if stripped.startswith('LICENSE') and '=' in stripped:
                license_line = line_num
                break
        
        if not license_line:
            return results
        
        # Check if any metadata vars appear after LICENSE
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            
            for meta_var in self.METADATA_VARS:
                if stripped.startswith(meta_var) and '=' in stripped:
                    if line_num > license_line:
                        results.append(self.create_result(
                            file=context,
                            line=line_num,
                            message=f"'{meta_var}' appears after LICENSE (line {license_line})",
                            hint=f"Place {meta_var} before LICENSE per Yocto style guide",
                        ))
        
        return results


class TaskOrderRule(BaseRule):
    """
    Check that task functions are in execution order.
    
    Tasks should generally be ordered by their execution order:
    do_fetch → do_unpack → do_patch → do_configure → do_compile → do_install → do_package
    """
    
    rule_id = "STYLE021"
    name = "Task Execution Order"
    description = "Check task functions follow execution order"
    default_severity = Severity.INFO
    groups = ["style", "ordering", "tasks"]
    hint = "Order tasks by execution: fetch → unpack → patch → configure → compile → install"
    enabled_by_default = True

    # Task execution order (lower = earlier)
    TASK_ORDER = {
        'do_fetch': 1,
        'do_unpack': 2,
        'do_patch': 3,
        'do_prepare_recipe_sysroot': 4,
        'do_configure': 5,
        'do_compile': 6,
        'do_install': 7,
        'do_populate_sysroot': 8,
        'do_package': 9,
        'do_package_write': 10,
    }
    
    # Pattern to detect task definitions
    TASK_PATTERN = re.compile(r'^(do_[a-z_]+)(?::[a-z_]+)?\s*\(')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Collect task positions
        task_positions = []  # List of (line_num, task_name, order)
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith('#'):
                continue
            
            match = self.TASK_PATTERN.match(stripped)
            if match:
                task_name = match.group(1)
                # Get base task name (without :append etc)
                base_task = task_name.split(':')[0] if ':' in task_name else task_name
                
                if base_task in self.TASK_ORDER:
                    order = self.TASK_ORDER[base_task]
                    task_positions.append((line_num, task_name, order))
        
        # Check for out-of-order tasks
        if len(task_positions) >= 2:
            for i in range(len(task_positions) - 1):
                curr_line, curr_task, curr_order = task_positions[i]
                next_line, next_task, next_order = task_positions[i + 1]
                
                if curr_order > next_order:
                    results.append(self.create_result(
                        file=context,
                        line=curr_line,
                        message=f"'{curr_task}' appears before '{next_task}' (should be after)",
                        hint="Order tasks by execution sequence: configure → compile → install",
                    ))
        
        return results
