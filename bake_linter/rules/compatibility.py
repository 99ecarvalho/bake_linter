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
    Check for a top-level alternation in COMPATIBLE_HOST.

    BitBake matches the value against the host triplet with ``re.match``
    (``meta/classes-global/base.bbclass``: ``if not re.match(need_host,
    this_host)``). A ``|`` outside any group splits the *whole* regex, so
    ``"x86_64|aarch64-linux"`` means "starts with x86_64, or starts with
    aarch64-linux", not "(x86_64 or aarch64)-linux". The intended form groups
    the alternatives: ``"(x86_64|aarch64).*-linux"``.

    A top-level alternation is accepted when every branch is a complete
    triplet pattern (contains a ``-``), e.g. ``"x86_64.*-linux|aarch64.*-linux"``.

    A leading ``^`` is not required: ``re.match`` is already anchored at the
    start, and poky writes unanchored values throughout (kexec-tools,
    igt-gpu-tools, systemtap, grub2).
    """

    rule_id = "COMPAT001"
    name = "Ungrouped COMPATIBLE_HOST Alternation"
    description = "Detects a top-level | in COMPATIBLE_HOST that splits the whole pattern"
    default_severity = Severity.WARNING
    groups = ["compatibility"]
    hint = "Group the alternatives, e.g. (x86_64|aarch64).*-linux"

    # Assignments that set the whole value; :append/:prepend/:remove fragments
    # are not complete patterns and are skipped.
    COMPAT_HOST_PATTERN = re.compile(
        r'^COMPATIBLE_HOST(?::(?!append\b|prepend\b|remove\b)[\w${}+-]+)*'
        r'\s*(?:\?\?|\?|:)?=\s*(["\'])(.*?)\1'
    )

    @staticmethod
    def _top_level_branches(pattern: str) -> List[str]:
        """Split *pattern* on ``|`` outside groups, classes and escapes."""
        branches, current = [], []
        depth, in_class, escaped = 0, False, False
        for char in pattern:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif in_class:
                in_class = char != "]"
            elif char == "[":
                in_class = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth = max(depth - 1, 0)
            elif char == "|" and depth == 0:
                branches.append("".join(current))
                current = []
                continue
            current.append(char)
        branches.append("".join(current))
        return branches

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            match = self.COMPAT_HOST_PATTERN.match(stripped)
            if not match:
                continue

            branches = self._top_level_branches(match.group(2))
            if len(branches) < 2 or all("-" in b for b in branches):
                continue

            results.append(self.create_result(
                file=context,
                line=line_num,
                message=(
                    f"COMPATIBLE_HOST \"{match.group(2)}\" has a top-level '|', "
                    "which splits the whole pattern instead of one part of it"
                ),
                context=stripped[:80],
                hint=self.hint,
            ))

        return results


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
        # Content that depends on the machine's configuration
        re.compile(r'\$\{MACHINE\}'),
        re.compile(r'MACHINEOVERRIDES'),
        re.compile(r'SERIAL_CONSOLES'),
        re.compile(r'\bKERNEL_\w+'),
        re.compile(r'virtual/kernel'),
        re.compile(r'\bPACKAGE_ARCHS\b'),
        re.compile(r'\bCOMBINED_FEATURES\b'),
        re.compile(r'\bUBOOT_\w+'),
        re.compile(r'\bTUNE_\w+'),
    ]

    # Built against the machine's kernel, producing no packages, or
    # deploying machine-specific output
    MACHINE_SPECIFIC_CLASSES = {
        "module", "kernel", "kernelsrc", "nopackages", "deploy", "toolchain-scripts",
    }

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        machine_arch_line = 0
        has_machine_arch = False
        has_justification = bool(context.inherits & self.MACHINE_SPECIFIC_CLASSES)

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
            has_justification = self._justified_in_includes(context)

        if has_machine_arch and not has_justification:
            results.append(self.create_result(
                file=context,
                line=machine_arch_line,
                message="PACKAGE_ARCH = \"${MACHINE_ARCH}\" without clear machine-specific code",
                hint="Remove MACHINE_ARCH unless recipe has machine-specific content",
            ))

        return results

    def _justified_in_includes(self, context: FileContext) -> bool:
        """Whether an included file has an indicator. True when an include
        was not found, since it may have one."""
        included = context.included_files
        if included is None:
            return True
        for include in included:
            try:
                lines = include.path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                return True
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if any(i.search(stripped) for i in self.MACHINE_SPECIFIC_INDICATORS):
                    return True
        return False
