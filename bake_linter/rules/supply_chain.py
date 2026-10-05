# -*- coding: utf-8 -*-
"""
Supply chain and reproducibility rules for Yocto recipes.

These rules check for source integrity and reproducibility issues.

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


class UnpinnedBranchRule(BaseRule):
    """
    Check for mutable branch references in git URIs that are not pinned.

    A mutable branch is a reproducibility hazard only when nothing pins the
    commit: what gets built is decided by SRCREV, and the branch is just the
    ref bitbake fetches and validates the revision against. So this rule fires
    on a mutable branch when the recipe has no pinned SRCREV, or uses AUTOREV.
    """

    rule_id = "REPRO001"
    name = "Unpinned Branch Usage"
    description = "Detects mutable branch references (master, main, develop) with no pinned SRCREV"
    default_severity = Severity.WARNING
    groups = ["reproducibility", "source"]
    hint = "Pin the commit with SRCREV, or use a stable/release branch"

    # Mutable development branches to flag
    MUTABLE_BRANCHES = ['master', 'main', 'develop', 'trunk', 'dev', 'development']

    GIT_URI_PATTERN = re.compile(r'(?:git|gitsm)://[^;]+;[^"\']*branch=([^;"\'\s]+)')

    # A 40-hex SRCREV pins the exact commit. Poky/meta-openembedded have 736
    # recipes on branch=master|main and 728 of them (98.9%) pin SRCREV this
    # way, so flagging the pinned case fires on the standard practice rather
    # than on a real hazard. AUTOREV is the genuinely unreproducible case and
    # is never treated as pinned, whatever else the recipe does.
    PINNED_SRCREV_PATTERN = re.compile(
        r'^SRCREV[A-Za-z0-9_:${}.-]*\s*[?:+]?=\s*"[0-9a-fA-F]{40}"'
    )
    AUTOREV_PATTERN = re.compile(r'\bAUTOREV\b')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        # The pinning state is a property of the whole recipe, so resolve it
        # before judging any individual URI line.
        has_pinned_srcrev = False
        uses_autorev = False
        for line in context.lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if self.PINNED_SRCREV_PATTERN.match(stripped):
                has_pinned_srcrev = True
            if self.AUTOREV_PATTERN.search(stripped):
                uses_autorev = True

        if has_pinned_srcrev and not uses_autorev:
            return results

        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()

            if stripped.startswith("#"):
                continue

            matches = self.GIT_URI_PATTERN.findall(line)
            for branch in matches:
                if branch.lower() in self.MUTABLE_BRANCHES:
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message=(
                            f"Mutable branch '{branch}' used in git URI with "
                            f"no pinned SRCREV"
                        ),
                        context=stripped[:60],
                        hint='Pin the commit (SRCREV = "<40-hex>") or use a stable/release branch',
                    ))
        
        return results


class MissingLicenseChecksumInBbappendRule(BaseRule):
    """
    Check for bbappend files adding sources without license verification.
    
    When adding new source files via bbappend, the license should be
    verified to ensure compatibility with the base recipe.
    """
    
    rule_id = "SUPPLY001"
    name = "Missing License Verification in bbappend"
    description = "Detects .bbappend adding sources without LIC_FILES_CHKSUM update"
    default_severity = Severity.WARNING
    groups = ["security", "license", "bbappend"]
    hint = "Verify license compatibility when adding new sources"
    
    applicable_file_types = {"bbappend"}

    # Matches every assignment form, including the :append/:prepend the
    # previous pattern (SRC_URI\s*[+:]?=) silently missed - which is the most
    # common form in a .bbappend.
    SRC_URI_MODIFY_PATTERN = re.compile(
        r'^SRC_URI(?::(?:append|prepend))?(?::[a-zA-Z0-9_${}+-]+)*\s*[+?:]?='
    )
    LIC_FILES_PATTERN = re.compile(r'LIC_FILES_CHKSUM')

    # LIC_FILES_CHKSUM pins the license text of the *fetched upstream source*,
    # so it only matters when the bbappend brings in such a source. A local
    # file:// entry (a patch, a config file, a service unit carried in the
    # layer) is not one, and real poky/OE bbappends that add patches do not
    # touch LIC_FILES_CHKSUM (meta-rust/librsvg, meta-clang/gdb,
    # meta-example-bsp/systemd). Flagging those was a false positive.
    REMOTE_FETCH_PATTERN = re.compile(
        r'\b(?:https?|ftps?|s?ftp|git|gitsm|svn|hg|bzr|osc|npm|npmsw|crate|'
        r'gs|s3|az|ssh)://'
    )

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        if not str(context.path).endswith('.bbappend'):
            return results

        adds_remote_source = False
        has_lic_check = False
        src_uri_line = 0
        in_src_uri = False

        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()

            if stripped.startswith("#"):
                continue

            if self.LIC_FILES_PATTERN.search(stripped):
                has_lic_check = True

            if not in_src_uri and self.SRC_URI_MODIFY_PATTERN.match(stripped):
                in_src_uri = True
                if src_uri_line == 0:
                    src_uri_line = line_num

            if in_src_uri:
                if self.REMOTE_FETCH_PATTERN.search(stripped):
                    adds_remote_source = True
                # The assignment ends on the first line not continued with '\'
                if not stripped.endswith('\\'):
                    in_src_uri = False

        if adds_remote_source and not has_lic_check:
            results.append(self.create_result(
                file=context,
                line=src_uri_line,
                message=(
                    "bbappend fetches upstream source without updating "
                    "LIC_FILES_CHKSUM"
                ),
                hint="Verify added sources have compatible licenses",
            ))

        return results


class UnreliableHostingRule(BaseRule):
    """
    Check for downloads from unreliable or temporary hosting services.
    
    Personal hosting, file sharing sites, and raw GitHub content have
    high disappearance risk and are not suitable for production builds.
    """
    
    rule_id = "SUPPLY002"
    name = "Unreliable Download Hosting"
    description = "Detects downloads from personal/temporary hosting services"
    default_severity = Severity.WARNING
    groups = ["security", "supply_chain", "source"]
    hint = "Use official release sources and configure MIRRORS for fallback"

    # Unreliable hosting patterns
    UNRELIABLE_HOSTS = [
        re.compile(r'dropbox\.com'),
        re.compile(r'drive\.google\.com'),
        re.compile(r'pastebin\.com'),
        re.compile(r'dl\.dropboxusercontent\.com'),
        re.compile(r'raw\.githubusercontent\.com'),
        re.compile(r'gist\.github\.com'),
        re.compile(r'mediafire\.com'),
        re.compile(r'mega\.nz'),
        re.compile(r'sendspace\.com'),
        re.compile(r'wetransfer\.com'),
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if 'SRC_URI' in stripped or 'http' in stripped.lower():
                for pattern in self.UNRELIABLE_HOSTS:
                    if pattern.search(stripped):
                        results.append(self.create_result(
                            file=context,
                            line=line_num,
                            message="Download from potentially unreliable hosting service",
                            context=stripped[:60],
                            hint="Use official release URLs and configure MIRRORS",
                        ))
                        break
        
        return results
