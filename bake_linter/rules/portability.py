# -*- coding: utf-8 -*-
"""
Portability rules for Yocto recipes.

These rules check for issues that affect cross-compilation and
portability across different architectures and build hosts.

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


class HardcodedCpuFlagsRule(BaseRule):
    """
    Check for hardcoded CPU architecture flags.
    
    Hardcoding -march, -mtune, or similar flags breaks cross-compilation
    and machine independence. Use tune file settings instead.
    """
    
    rule_id = "PORT001"
    name = "Hardcoded CPU Architecture Flags"
    description = "Detects hardcoded -march/-mtune/etc. in compiler flags"
    default_severity = Severity.WARNING
    groups = ["portability", "cross-compile"]
    hint = "Use TUNE_CCARGS or machine/tune configuration instead"

    CPU_FLAG_PATTERNS = [
        re.compile(r'-march=\w+'),
        re.compile(r'-mtune=\w+'),
        re.compile(r'-mcpu=\w+'),
        re.compile(r'-mfpu=\w+'),
        re.compile(r'-mfloat-abi=\w+'),
        re.compile(r'-mabi=\w+'),
        re.compile(r'-m32\b'),
        re.compile(r'-m64\b'),
    ]
    
    FLAG_VARIABLES = ['CFLAGS', 'CXXFLAGS', 'TARGET_CFLAGS', 'TARGET_CXXFLAGS',
                      'EXTRA_OECMAKE', 'EXTRA_OECONF', 'EXTRA_OEMAKE']

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Check if this line modifies flag variables
            is_flag_var = any(var in stripped for var in self.FLAG_VARIABLES)
            
            if is_flag_var:
                for pattern in self.CPU_FLAG_PATTERNS:
                    match = pattern.search(stripped)
                    if match:
                        results.append(self.create_result(
                            file=context,
                            line=line_num,
                            message=f"Hardcoded CPU flag: {match.group()}",
                            context=stripped[:60],
                            hint="Let tune files control CPU-specific flags",
                        ))
                        break  # One warning per line
        
        return results


class AbsoluteHostPathRule(BaseRule):
    """
    Check for absolute host filesystem paths where they affect the build.
    
    A compiler or linker search path such as -I/usr/include or -L/usr/lib
    makes the build pick up the build host's headers and libraries instead of
    the sysroot's, and a configure, CMake or Meson path option set to
    /usr/lib or /opt bypasses ${libdir}, ${prefix} and friends. An install
    command in do_install that does not write below ${D} writes to the build
    host.
    
    Only build-affecting places are checked: the flag and configure option
    variables, PACKAGECONFIG, and the do_configure, do_compile and do_install
    bodies. Elsewhere an absolute path usually names a location on the target
    (pkg_postinst scripts, ALTERNATIVE_*, documentation, sed expressions
    rewriting installed files), which is not a host path at all. Sysroot
    relative paths (-I=/usr/include) are fine.
    """
    
    rule_id = "PORT002"
    name = "Absolute Host Paths"
    description = "Detects absolute host paths in build flags, configure options and build tasks"
    default_severity = Severity.WARNING
    groups = ["portability", "cross-compile", "sysroot"]
    hint = "Use Yocto variables like ${STAGING_DIR_TARGET} instead"

    # Host locations a build-affecting path option should not name
    HOST_DIRS = r'/(?:usr|opt|home|lib(?:32|64)?|etc)\b'

    BUILD_PATH_PATTERNS = [
        # Compiler and linker search paths (but not -I=/usr: sysroot relative)
        re.compile(r'(?<![\w-])(?:-I|-isystem\s*|-L|-Wl,-rpath-link[=,])/'),
        re.compile(r'\bPKG_CONFIG_PATH=/'),
        # Autotools directory options
        re.compile(r'(?<![\w-])--(?:prefix|exec-prefix|(?:bin|sbin|libexec|sysconf|'
                   r'sharedstate|localstate|lib|include|oldinclude|data|dataroot|'
                   r'info|locale|man|doc)dir)=' + HOST_DIRS),
        re.compile(r'(?<![\w-])--with-[\w-]*(?:include|lib|dir|prefix)[\w-]*=' + HOST_DIRS),
        # CMake and Meson directory options
        re.compile(r'(?<![\w-])-D\w*(?:INCLUDE|LIB|PREFIX|DIR)\w*(?::\w+)?=' + HOST_DIRS,
                   re.IGNORECASE),
    ]
    
    # do_install writing outside ${D}: install/cp/mkdir/touch to /usr, /etc...
    HOST_WRITE_PATTERN = re.compile(
        r'^(?:install|cp|mkdir|touch)\s.*\s["\']?/(?:usr|etc|opt|lib|var|bin|sbin)\b')

    # A sed command, or an -e expression continuing one
    SED_PATTERN = re.compile(r'(?:^|[|;&\s])sed\s|^-e\s')

    # Variables whose value goes to the compiler, linker or configure step
    BUILD_VARIABLES = {
        'CFLAGS', 'CPPFLAGS', 'CXXFLAGS', 'LDFLAGS',
        'TARGET_CFLAGS', 'TARGET_CPPFLAGS', 'TARGET_CXXFLAGS', 'TARGET_LDFLAGS',
        'EXTRA_OECONF', 'EXTRA_OECMAKE', 'EXTRA_OEMAKE', 'EXTRA_OEMESON',
        'EXTRA_OESCONS', 'PACKAGECONFIG', 'PACKAGECONFIG_CONFARGS',
    }
    BUILD_TASKS = ('do_configure', 'do_compile')
    INSTALL_TASK = 'do_install'

    # Contexts where host paths are acceptable
    ACCEPTABLE_CONTEXTS = [
        'TOOLCHAIN_HOST_TASK',
        'SYSROOT_DIRS_NATIVE',
        'HOST_',  # Any HOST_* variables
        'native.bbclass',
        '-native',
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        if '-native' in str(context.path):
            return results
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if not stripped or stripped.startswith("#"):
                continue
            if any(ctx in stripped for ctx in self.ACCEPTABLE_CONTEXTS):
                continue
            # A sed expression that rewrites a host path out of a Makefile
            # (s:-I/usr/include:-I${STAGING_INCDIR}:) is the fix, not a use
            if self.SED_PATTERN.search(stripped):
                continue

            owner = context.owner_base(line_num)
            function = owner[len("FUNC:"):].split(':', 1)[0] if owner.startswith("FUNC:") else None

            if owner in self.BUILD_VARIABLES or function in self.BUILD_TASKS:
                found = any(p.search(stripped) for p in self.BUILD_PATH_PATTERNS)
            elif function == self.INSTALL_TASK:
                found = ('${D}' not in stripped
                         and bool(self.HOST_WRITE_PATTERN.search(stripped)))
            else:
                continue

            if found:
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message="Absolute host path may break cross-compilation",
                    context=stripped[:60],
                    hint="Use ${D}, ${STAGING_DIR_TARGET}, ${libdir}, etc.",
                ))
        
        return results


class NonPortableSedRule(BaseRule):
    """
    Check for non-portable sed patterns.
    
    Some sed features are GNU-specific and may not work with BusyBox
    or BSD sed commonly found in target systems.
    """
    
    rule_id = "PORT003"
    name = "Non-Portable Sed Usage"
    description = "Detects GNU-specific sed features"
    default_severity = Severity.INFO
    groups = ["portability", "shell"]
    hint = "Use POSIX-compliant sed for better portability"

    # GNU-specific sed patterns
    GNU_SED_PATTERNS = [
        (re.compile(r'\bsed\s+.*-i(?!\s*"")'), "sed -i without backup suffix (GNU-specific)"),
        (re.compile(r'\bsed\s+.*-r\b'), "sed -r (use -E for extended regex)"),
        (re.compile(r'\bsed\s+.*\\d'), "\\d digit class (use [0-9])"),
        (re.compile(r'\bsed\s+.*\\w'), "\\w word class (use [a-zA-Z0-9_])"),
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_task = False
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Track task context
            if re.match(r'^(do_\w+|fakeroot\s+do_\w+)\s*\(\)\s*\{', stripped):
                in_task = True
                continue
            
            if in_task and stripped == '}':
                in_task = False
                continue
            
            if in_task and 'sed' in stripped:
                for pattern, msg in self.GNU_SED_PATTERNS:
                    if pattern.search(stripped):
                        results.append(self.create_result(
                            file=context,
                            line=line_num,
                            message=msg,
                            context=stripped[:60],
                        ))
        
        return results
