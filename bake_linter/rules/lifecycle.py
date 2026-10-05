# -*- coding: utf-8 -*-
"""
Lifecycle and maintenance rules for Yocto recipes.

These rules check for metadata that helps with recipe maintenance
and version tracking.

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


class MissingUpstreamCheckRule(BaseRule):
    """
    Check for missing UPSTREAM_CHECK configuration.
    
    UPSTREAM_CHECK_* variables enable automated version upgrade detection
    using tools like devtool check-upgrade-status.
    """
    
    rule_id = "LIFECYCLE001"
    name = "Missing Upstream Check Configuration"
    description = "Detects recipes without UPSTREAM_CHECK for version tracking"
    default_severity = Severity.INFO
    groups = ["maintenance", "upstream"]
    hint = "Add UPSTREAM_CHECK_URI and UPSTREAM_CHECK_REGEX for version tracking"
    
    applicable_file_types = {"bb"}

    UPSTREAM_CHECK_VARS = [
        'UPSTREAM_CHECK_URI',
        'UPSTREAM_CHECK_REGEX',
        'UPSTREAM_CHECK_GITTAGREGEX',
        'UPSTREAM_CHECK_COMMITS',
    ]

    # Skip recipes that typically don't need upstream checks
    SKIP_PATTERNS = [
        r'-native\.bb$',
        r'-cross\.bb$',
        r'-image.*\.bb$',
        r'packagegroup-.*\.bb$',
    ]

    # LICENSE = "CLOSED" is the conventional marker for a proprietary recipe.
    # There is no public release feed to poll for such a recipe, so
    # UPSTREAM_CHECK_* has nothing to point at, and upstream layers do not set
    # it on CLOSED recipes. Only the exact value counts, the same value OE
    # special-cases: a compound expression ("CLOSED & GPL-2.0-or-later") has
    # an open part that usually does have a public upstream.
    CLOSED_LICENSE_PATTERN = re.compile(r'^LICENSE[^=]*=\s*"\s*CLOSED\s*"')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Only check .bb files
        if not str(context.path).endswith('.bb'):
            return results
        
        # Skip certain recipe types
        filename = str(context.path)
        for pattern in self.SKIP_PATTERNS:
            if re.search(pattern, filename):
                return results
        
        has_upstream_check = False
        has_src_uri = False
        is_closed = False

        for line in context.lines:
            stripped = line.strip()

            if stripped.startswith("#"):
                continue

            # Check for SRC_URI (indicates fetchable source)
            if 'SRC_URI' in stripped and '=' in stripped:
                has_src_uri = True

            if self.CLOSED_LICENSE_PATTERN.match(stripped):
                is_closed = True

            # Check for any upstream check variable
            for var in self.UPSTREAM_CHECK_VARS:
                if var in stripped:
                    has_upstream_check = True
                    break

        # A proprietary recipe has no public release feed to point at
        if is_closed:
            return results

        # Only flag if recipe has SRC_URI but no upstream check
        if has_src_uri and not has_upstream_check:
            results.append(self.create_result(
                file=context,
                line=1,
                message="Recipe lacks UPSTREAM_CHECK_* for version tracking",
                hint='Add: UPSTREAM_CHECK_URI = "https://..." and UPSTREAM_CHECK_REGEX = "..."',
            ))
        
        return results
