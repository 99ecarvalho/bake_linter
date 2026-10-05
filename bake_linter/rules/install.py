# -*- coding: utf-8 -*-
"""
Install command rules for Yocto recipes.

These rules check for proper file installation patterns in do_install tasks.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class CpInsteadOfInstallRule(BaseRule):
    """
    Check for cp command usage instead of install in do_install.

    Copying into ${D} with options that preserve ownership (-a, -p,
    --preserve=ownership or all) carries the build user's uid and gid into
    the package: do_install runs under pseudo, which records the copied
    ownership, and package QA reports host-user-contaminated files.

    Other copies into ${D} are reported as info: install is preferred
    because:
    - install can set permissions in one command
    - install can create directories
    - Makes permission expectations explicit

    For recursive copies (cp -r), suggests using find + install pattern.
    """

    rule_id = "INSTALL001"
    name = "Using cp Instead of install"
    description = "Detects cp in do_install that preserves ownership, or that could be install"
    default_severity = Severity.WARNING
    groups = ["install", "best_practices"]
    hint = "Use 'install -m MODE' instead of 'cp' for explicit permissions"

    DESTDIR = re.compile(r'\$\{D\}|\$D(?![A-Za-z0-9_])')
    # do_install, do_install_ptest, ...
    INSTALL_TASK = re.compile(r'^do_install(?:_\w+)?$')
    OWNERSHIP_HINT = (
        "cp preserves ownership; use --no-preserve=ownership or "
        "cp -R --no-dereference --preserve=mode,links"
    )

    @staticmethod
    def _attributes(value: str) -> set:
        return {a.strip() for a in value.split(",") if a.strip()}

    def _classify(self, options: List[str]) -> str:
        """"ownership" when the copy preserves ownership, "chosen" when the
        attributes to keep were chosen without ownership, "recursive" or
        "plain" otherwise."""
        preserves_ownership = False
        chosen = False
        recursive = False
        for option in options:
            if option.startswith("--no-preserve="):
                if self._attributes(option.split("=", 1)[1]) & {"ownership", "all"}:
                    return "chosen"
            elif option == "--preserve":
                # Defaults to mode,ownership,timestamps
                preserves_ownership = True
            elif option.startswith("--preserve="):
                if self._attributes(option.split("=", 1)[1]) & {"ownership", "all"}:
                    preserves_ownership = True
                else:
                    chosen = True
            elif option == "--archive":
                preserves_ownership = recursive = True
            elif option == "--recursive":
                recursive = True
            elif not option.startswith("--"):
                letters = option[1:]
                if "a" in letters or "p" in letters:
                    preserves_ownership = True
                if any(c in letters for c in "rRa"):
                    recursive = True
        if preserves_ownership:
            return "ownership"
        if chosen:
            return "chosen"
        return "recursive" if recursive else "plain"

    def check(self, context: FileContext) -> List[LintResult]:
        from bake_linter.core.recipe import command_words
        results = []

        for line in context.function_lines:
            if not self.INSTALL_TASK.match(line.function.split(":", 1)[0]):
                continue
            words = command_words(line.text)
            if words[:1] != ["cp"]:
                continue
            options = [w for w in words[1:] if w.startswith("-") and len(w) > 1]
            operands = [w for w in words[1:] if w not in options]
            # Only copies into the install tree
            if not any(self.DESTDIR.search(w) for w in operands):
                continue

            kind = self._classify(options)
            if kind == "chosen":
                continue
            if kind == "ownership":
                results.append(self.create_result(
                    file=context,
                    line=line.line,
                    message="cp preserves ownership; use --no-preserve=ownership or "
                            "cp -R --no-dereference --preserve=mode,links",
                    context=line.text[:60],
                    hint=self.OWNERSHIP_HINT,
                ))
                continue

            if kind == "recursive":
                hint = (
                    "For recursive copy, use find + install: "
                    "find src -type d -exec install -d dest/{} \\; && "
                    "find src -type f -exec install -m 0644 {} dest/{} \\;"
                )
            else:
                hint = "Use 'install -d' for dirs, 'install -m MODE' for files"

            results.append(self.create_result(
                file=context,
                line=line.line,
                message="Using 'cp' instead of 'install' command",
                context=line.text[:60],
                hint=hint,
                severity=Severity.INFO,
            ))

        return results


class InstallWithoutModeRule(BaseRule):
    """
    Check for install commands without explicit permission mode.
    
    Relying on default umask for permissions can lead to:
    - Inconsistent file permissions across builds
    - Security issues from overly permissive defaults
    - Unexpected behavior in different build environments
    """
    
    rule_id = "INSTALL002"
    name = "Install Without Explicit Mode"
    description = "Detects install commands without explicit -m permission mode"
    default_severity = Severity.WARNING
    groups = ["install", "security"]
    hint = "Add '-m 0755' for binaries, '-m 0644' for data files"

    # Pattern to detect install command (not install -d which doesn't need -m)
    # Looking for install commands that copy files (not just -d for directory)
    INSTALL_PATTERN = re.compile(r'^\s*install\s+')
    
    # Pattern to detect -d flag (directory creation, doesn't need -m)
    DIR_FLAG_PATTERN = re.compile(r'\s-d\s')
    
    # Pattern to detect -m flag (handles various valid forms):
    # -m 0644, -m0644, -Dm 0644, -Dm0644, -D -m 0644, etc.
    MODE_FLAG_PATTERN = re.compile(r'-[A-Za-z]*m\s*[0-7]{3,4}')
    
    # Pattern to detect we're in a do_install task
    INSTALL_TASK_PATTERN = re.compile(r'^do_install(?:[_:]|$|\s*\(\))')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_do_install = False
        brace_depth = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            # Track if we're inside do_install
            if self.INSTALL_TASK_PATTERN.match(stripped):
                in_do_install = True
                if '{' in stripped:
                    brace_depth = 1
                continue
            
            # Track brace depth
            if in_do_install:
                brace_depth += stripped.count('{') - stripped.count('}')
                if brace_depth <= 0:
                    in_do_install = False
                    brace_depth = 0
                    continue
                
                # Check for install command without -m (but not -d only)
                if self.INSTALL_PATTERN.match(stripped):
                    # Skip if it's just directory creation (-d flag present, no source files)
                    if self.DIR_FLAG_PATTERN.search(stripped):
                        # Check if there are source files after -d (install -d dir is ok, install -d -m ... src dst needs -m)
                        # Simple heuristic: if -d is the only flag before ${D}, it's just dir creation
                        if stripped.count('${D}') == 1 and not self.MODE_FLAG_PATTERN.search(stripped):
                            continue
                    
                    # Check if -m flag is present
                    if not self.MODE_FLAG_PATTERN.search(stripped):
                        # Skip pure directory creation
                        if self.DIR_FLAG_PATTERN.search(stripped) and stripped.count('$') <= 2:
                            continue
                        
                        results.append(self.create_result(
                            file=context,
                            line=line_num,
                            message="install command without explicit -m permission mode",
                            context=stripped[:60],
                            hint="Add -m 0755 for executables, -m 0644 for data files",
                        ))
        
        return results


class MkdirInsteadOfInstallDRule(BaseRule):
    """
    Check for mkdir -p usage instead of install -d in do_install.
    
    Using install -d is preferred because:
    - Sets consistent ownership and permissions
    - Standard Yocto/OE practice
    - More explicit about intent
    """
    
    rule_id = "INSTALL003"
    name = "mkdir Instead of install -d"
    description = "Detects mkdir -p usage instead of install -d in do_install"
    default_severity = Severity.INFO
    groups = ["install", "best_practices"]
    hint = "Use 'install -d' instead of 'mkdir -p'"

    MKDIR_PATTERN = re.compile(r'^\s*mkdir\s+(?:-p\s+)?')
    INSTALL_TASK_PATTERN = re.compile(r'^do_install(?:[_:]|$|\s*\(\))')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_do_install = False
        brace_depth = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
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
                
                if self.MKDIR_PATTERN.match(stripped):
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message="Using 'mkdir' instead of 'install -d'",
                        context=stripped[:60],
                        hint="Replace 'mkdir -p' with 'install -d' for consistency",
                    ))
        
        return results


class UsrLocalInstallRule(BaseRule):
    """
    Check for installations to /usr/local which is non-standard for Yocto.
    
    /usr/local is inappropriate for Yocto builds because:
    - Conflicts with package management
    - Not part of standard Yocto FHS
    - May cause rootfs inconsistencies
    """
    
    rule_id = "INSTALL004"
    name = "Installation to /usr/local"
    description = "Detects installations to /usr/local which is non-standard for Yocto"
    default_severity = Severity.WARNING
    groups = ["install", "portability"]
    hint = "Use ${bindir}, ${libdir}, ${datadir} instead of /usr/local/*"

    USR_LOCAL_PATTERN = re.compile(r'/usr/local(?![\w.-])')
    # Places where /usr/local is where files end up: below ${D}, or as the
    # install prefix handed to the build system
    INSTALL_PATTERNS = [
        re.compile(r'\$\{D\}/usr/local(?:/|\b)'),
        re.compile(r'(?<![\w-])(?:--)?prefix=["\']?/usr/local\b', re.IGNORECASE),
        re.compile(r'-DCMAKE_INSTALL_PREFIX(?::\w+)?=["\']?/usr/local\b'),
        re.compile(r'^(?:export\s+)?prefix\s*(?:\?\??|:)?=\s*["\']/usr/local\b'),
    ]
    # A sed command, or an -e expression continuing one: rewriting
    # /usr/local out of a file is the fix, not an install there
    SED_PATTERN = re.compile(r'(?:^|[|;&\s])sed\s|^-e\s')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            if not self.USR_LOCAL_PATTERN.search(line):
                continue
            if self.SED_PATTERN.search(stripped):
                continue

            # A FILES value packages /usr/local; elsewhere only an install
            # destination or prefix counts
            in_files = context.owner_base(line_num) == "FILES"
            if in_files or any(p.search(stripped) for p in self.INSTALL_PATTERNS):
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message="Installation to /usr/local is non-standard for Yocto",
                    context=stripped[:60],
                    hint="Use standard variables: ${bindir}, ${libdir}, ${datadir}",
                ))
        
        return results


class NonFHSPathRule(BaseRule):
    """
    Check for installations outside standard FHS paths.
    
    Detects files installed to non-standard locations that may cause:
    - Package management issues
    - Portability problems
    - Maintenance difficulties
    
    Note: Recognizes BitBake variables like ${bindir}, ${libdir} as FHS-compliant.
    Paths like ${D}/${bindir} or ${D}${bindir} are both valid and compliant.
    """
    
    rule_id = "INSTALL005"
    name = "Non-FHS Installation Path"
    description = "Detects files installed outside standard FHS paths"
    default_severity = Severity.INFO
    groups = ["install", "portability"]
    hint = "Use standard paths: ${bindir}, ${libdir}, ${datadir}, ${sysconfdir}"

    # FHS-compliant BitBake variables - these are always valid destinations
    FHS_VARIABLES = [
        'bindir', 'sbindir', 'libdir', 'libexecdir', 'datadir',
        'sysconfdir', 'localstatedir', 'includedir', 'docdir',
        'mandir', 'infodir', 'sharedstatedir', 'servicedir',
        'systemd_system_unitdir', 'systemd_user_unitdir', 'systemd_unitdir',
        'base_bindir', 'base_sbindir', 'base_libdir',
        'nonarch_libdir', 'nonarch_base_libdir',
    ]

    # Standard FHS paths (as variables or literals)
    STANDARD_PATHS = [
        r'\$\{D\}\$\{bindir\}',
        r'\$\{D\}\$\{sbindir\}',
        r'\$\{D\}\$\{libdir\}',
        r'\$\{D\}\$\{libexecdir\}',
        r'\$\{D\}\$\{datadir\}',
        r'\$\{D\}\$\{sysconfdir\}',
        r'\$\{D\}\$\{localstatedir\}',
        r'\$\{D\}\$\{includedir\}',
        r'\$\{D\}\$\{docdir\}',
        r'\$\{D\}\$\{mandir\}',
        r'\$\{D\}\$\{infodir\}',
        r'\$\{D\}\$\{systemd_system_unitdir\}',
        r'\$\{D\}\$\{systemd_user_unitdir\}',
        r'\$\{D\}/usr/',
        r'\$\{D\}/etc/',
        r'\$\{D\}/var/',
        r'\$\{D\}/opt/',
        r'\$\{D\}/lib/',
        r'\$\{D\}/run/',
        r'\$\{D\}/srv/',
        r'\$\{D\}/home/',
    ]
    
    STANDARD_PATTERN = re.compile('|'.join(STANDARD_PATHS))
    INSTALL_TASK_PATTERN = re.compile(r'^do_install(?:[_:]|$|\s*\(\))')
    INSTALL_PATTERN = re.compile(r'^\s*install\s+.*\$\{D\}(/\S+)')

    def _uses_fhs_variable(self, path: str) -> bool:
        """Check if the path uses any FHS-compliant BitBake variable."""
        for var in self.FHS_VARIABLES:
            # Match ${var} or ${var}/subpath patterns
            if f'${{{var}}}' in path or f'${{{var}/' in path:
                return True
        return False

    def _is_fhs_compliant(self, path: str) -> bool:
        """Check if the path is FHS-compliant (variable or literal)."""
        # If it uses an FHS variable, it's compliant
        if self._uses_fhs_variable(path):
            return True
        
        # Check for standard literal paths
        fhs_roots = ['/usr', '/etc', '/var', '/opt', '/lib', '/run', '/srv', '/home', '/boot']
        return any(path.startswith(root) or f'/{root[1:]}' in path for root in fhs_roots)

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_do_install = False
        brace_depth = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
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
                
                # Check for install commands with non-standard destinations
                if 'install ' in stripped and '${D}' in stripped:
                    # Skip if using standard paths (legacy pattern check)
                    if self.STANDARD_PATTERN.search(stripped):
                        continue
                    
                    # Extract the destination path
                    match = self.INSTALL_PATTERN.search(stripped)
                    if match:
                        dest_path = match.group(1)
                        
                        # Check if it's FHS-compliant (variable or literal)
                        if not self._is_fhs_compliant(dest_path):
                            results.append(self.create_result(
                                file=context,
                                line=line_num,
                                message=f"Installation to non-FHS path: {dest_path}",
                                context=stripped[:60],
                                hint="Consider using standard FHS paths",
                            ))
        
        return results

