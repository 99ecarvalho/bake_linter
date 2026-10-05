# -*- coding: utf-8 -*-
"""
Compatibility rules for Yocto recipes.

These rules check for compatibility and portability issues.

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


class DeprecatedCompatibleHostRule(BaseRule):
    """
    Check for improper COMPATIBLE_HOST patterns.

    This rule used to require a leading ``^`` anchor. That was wrong on two
    counts, so it no longer fires:

    - BitBake matches the value with ``re.match``
      (``meta/classes-global/base.bbclass``: ``if not re.match(need_host,
      this_host)``), which is already anchored at the start. A leading ``^``
      changes nothing.
    - The vendored poky tree writes unanchored values throughout:
      ``kexec-tools_2.0.28.bb``
      (``'(x86_64.*|i.86.*|arm.*|aarch64.*|powerpc.*|mips.*)-(linux|freebsd.*)'``),
      ``igt-gpu-tools_git.bb``, ``systemtap_git.inc``, ``grub2.inc``.

    An unparenthesised alternation would be a genuine defect worth flagging
    (``"x86_64|aarch64-linux"`` does not mean what it looks like), but the
    vendored trees contain no instance of it, so nothing is implemented for it
    here rather than guessing at a pattern. Do not restore the ``^``
    requirement.
    """

    rule_id = "COMPAT001"
    name = "Deprecated COMPATIBLE_HOST Syntax"
    description = "Detects deprecated or improper COMPATIBLE_HOST patterns"
    default_severity = Severity.WARNING
    groups = ["compatibility", "deprecated"]
    hint = "Use a grouped regex, e.g. (x86_64.*|aarch64.*)-linux"

    COMPAT_HOST_PATTERN = re.compile(r'^COMPATIBLE_HOST\s*=\s*["\']([^"\']+)["\']')

    def check(self, context: FileContext) -> List[LintResult]:
        return []


class UnjustifiedMachineArchRule(BaseRule):
    """
    Check for PACKAGE_ARCH = "${MACHINE_ARCH}" without machine-specific code.
    
    Using MACHINE_ARCH when not necessary reduces sstate reuse and
    increases build times.
    """
    
    rule_id = "COMPAT002"
    name = "Unjustified MACHINE_ARCH"
    description = "Detects PACKAGE_ARCH = \"${MACHINE_ARCH}\" without clear justification"
    default_severity = Severity.WARNING
    groups = ["compatibility", "performance"]
    hint = "Only use MACHINE_ARCH for truly machine-specific content"

    MACHINE_ARCH_PATTERN = re.compile(r'PACKAGE_ARCH\s*=\s*["\']?\$\{MACHINE_ARCH\}["\']?')
    
    # Indicators of legitimate machine-specific recipes
    MACHINE_SPECIFIC_INDICATORS = [
        re.compile(r'inherit\s+module'),  # Kernel module
        re.compile(r'inherit\s+kernel'),  # Kernel recipe
        re.compile(r'MACHINE_FEATURES'),
        re.compile(r'KERNEL_MODULE'),
        re.compile(r'MACHINE_EXTRA'),
        re.compile(r'COMPATIBLE_MACHINE'),
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        machine_arch_line = 0
        has_machine_arch = False
        has_justification = False
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if self.MACHINE_ARCH_PATTERN.search(stripped):
                has_machine_arch = True
                machine_arch_line = line_num
            
            for indicator in self.MACHINE_SPECIFIC_INDICATORS:
                if indicator.search(stripped):
                    has_justification = True
                    break
        
        if has_machine_arch and not has_justification:
            results.append(self.create_result(
                file=context,
                line=machine_arch_line,
                message="PACKAGE_ARCH = \"${MACHINE_ARCH}\" without clear machine-specific code",
                hint="Remove MACHINE_ARCH unless recipe has machine-specific content",
            ))
        
        return results
