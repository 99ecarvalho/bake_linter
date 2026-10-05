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
from typing import List, Optional

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class UnpinnedBranchRule(BaseRule):
    """
    Check for mutable branch references in git URIs that are not pinned.

    A mutable branch is a reproducibility hazard only when nothing pins the
    commit: what gets built is decided by SRCREV, and the branch is just the
    ref bitbake fetches and validates the revision against. So this rule fires
    on a mutable branch when the SRCREV for that URI (SRCREV_<name> for a URI
    with ;name=, SRCREV otherwise) is not a fixed commit, or is AUTOREV.
    """

    rule_id = "REPRO001"
    name = "Unpinned Branch Usage"
    description = "Detects mutable branch references (master, main, develop) with no pinned SRCREV"
    default_severity = Severity.WARNING
    groups = ["reproducibility", "source"]
    hint = "Pin the commit with SRCREV, or use a stable/release branch"

    # Mutable development branches to flag
    MUTABLE_BRANCHES = ['master', 'main', 'develop', 'trunk', 'dev', 'development']

    # A git or gitsm URI with its parameters
    GIT_URI_PATTERN = re.compile(r'\bgit(?:sm)?://[^"\'\s\\]+')
    BRANCH_PARAM = re.compile(r';branch=([^;"\'\s\\]+)')
    NAME_PARAM = re.compile(r';name=([^;"\'\s\\]+)')

    # A 40-hex SRCREV pins the exact commit. Poky/meta-openembedded have 736
    # recipes on branch=master|main and 728 of them (98.9%) pin SRCREV this
    # way, so flagging the pinned case fires on the standard practice rather
    # than on a real hazard. AUTOREV is the genuinely unreproducible case and
    # is never treated as pinned.
    #
    # Each URI is pinned by the SRCREV for its ;name= (SRCREV_<name>), falling
    # back to plain SRCREV as bitbake does, so a multi-repo recipe must pin
    # each repository. Overrides (SRCREV:pn-foo, SRCREV_foo:qemuarm) count
    # for the same name.
    SRCREV_PATTERN = re.compile(
        r'^SRCREV(?:_(?P<name>[A-Za-z0-9${}.-]+?))?(?::[A-Za-z0-9_${}.-]+)*'
        r'\s*(?:\?\?|\?|:)?=\s*(?P<quote>["\'])(?P<value>.*?)(?P=quote)'
    )
    HEX_REVISION = re.compile(r'^[0-9a-fA-F]{40}$')
    AUTOREV_PATTERN = re.compile(r'\bAUTOREV\b')

    def _srcrev_states(self, lines) -> dict:
        """Map each SRCREV name ("default" for plain SRCREV) to whether it is
        a fixed commit. AUTOREV anywhere for a name makes it unpinned."""
        states = {}
        for line in lines:
            match = self.SRCREV_PATTERN.match(line.strip())
            if not match:
                continue
            name = match.group("name") or "default"
            value = match.group("value").strip()
            if self.AUTOREV_PATTERN.search(value):
                states[name] = False
            elif self.HEX_REVISION.match(value):
                states.setdefault(name, True)
        return states

    def _included_states(self, context: FileContext) -> Optional[dict]:
        """SRCREV states set by the files this one requires or includes, or
        None when one of them cannot be found."""
        included = context.included_files
        if included is None:
            return None
        lines = []
        for item in included:
            try:
                lines += item.path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                return None
        return self._srcrev_states(lines)

    @staticmethod
    def _has_state(states: dict, name: str) -> bool:
        return name in states or "default" in states

    @staticmethod
    def _is_pinned(states: dict, name: str) -> bool:
        """bitbake looks up SRCREV_<name>, then falls back to plain SRCREV
        (fetch2 srcrev_internal_helper)."""
        if name in states:
            return states[name]
        return states.get("default", False)

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        # The pinning state is a property of the whole recipe, so resolve it
        # before judging any individual URI line.
        states = self._srcrev_states(context.lines)
        included_states = None

        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()

            if stripped.startswith("#"):
                continue

            for uri in self.GIT_URI_PATTERN.findall(line):
                branch = self.BRANCH_PARAM.search(uri)
                if not branch or branch.group(1).lower() not in self.MUTABLE_BRANCHES:
                    continue
                name = self.NAME_PARAM.search(uri)
                name = name.group(1) if name else "default"
                uri_states = states
                if not self._has_state(states, name):
                    # The SRCREV may be set by a file this one includes. An
                    # .inc is itself included by recipes that may pin it, and
                    # an include that cannot be found may set it: unknown.
                    if context.file_type == "include":
                        continue
                    if included_states is None:
                        included_states = self._included_states(context)
                    if included_states is None:
                        continue
                    uri_states = included_states
                if self._is_pinned(uri_states, name):
                    continue
                srcrev = "SRCREV" if name == "default" else f"SRCREV_{name}"
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message=(
                        f"Mutable branch '{branch.group(1)}' used in git URI with "
                        f"no pinned {srcrev}"
                    ),
                    context=stripped[:60],
                    hint=f'Pin the commit ({srcrev} = "<40-hex>") or use a stable/release branch',
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
    # layer) is not one, and real bbappends that add patches do not touch
    # LIC_FILES_CHKSUM (e.g. meta-clang's gdb bbappend). Flagging those was a
    # false positive.
    REMOTE_FETCH_PATTERN = re.compile(
        r'\b(?:https?|ftps?|s?ftp|git|gitsm|svn|hg|bzr|osc|npm|npmsw|crate|'
        r'gs|s3|az|ssh)://'
    )

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        if not str(context.path).endswith('.bbappend'):
            return results

        has_lic_check = False
        # Line of the first remote fetch, which is what the finding is about
        remote_line = 0
        in_src_uri = False

        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()

            if stripped.startswith("#"):
                continue

            if self.LIC_FILES_PATTERN.search(stripped):
                has_lic_check = True

            if not in_src_uri and self.SRC_URI_MODIFY_PATTERN.match(stripped):
                in_src_uri = True

            if in_src_uri:
                if remote_line == 0 and self.REMOTE_FETCH_PATTERN.search(stripped):
                    remote_line = line_num
                # The assignment ends on the first line not continued with '\'
                if not stripped.endswith('\\'):
                    in_src_uri = False

        if remote_line and not has_lic_check:
            results.append(self.create_result(
                file=context,
                line=remote_line,
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

    RAW_GITHUB = re.compile(r'raw\.githubusercontent\.com')

    # Unreliable hosting patterns
    UNRELIABLE_HOSTS = [
        re.compile(r'dropbox\.com'),
        re.compile(r'drive\.google\.com'),
        re.compile(r'pastebin\.com'),
        re.compile(r'dl\.dropboxusercontent\.com'),
        RAW_GITHUB,
        re.compile(r'gist\.github\.com'),
        re.compile(r'mediafire\.com'),
        re.compile(r'mega\.nz'),
        re.compile(r'sendspace\.com'),
        re.compile(r'wetransfer\.com'),
    ]

    # raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>. The file is
    # served from git, so a ref that is a commit id, or the release tag of
    # the version being built, names content that does not change.
    RAW_GITHUB_REF = re.compile(
        r'raw\.githubusercontent\.com/[^/\s]+/[^/\s]+/(?P<ref>[^/\s;"\']+)'
    )
    FIXED_REF = re.compile(r'^[0-9a-fA-F]{40}$|\$\{PV\}')

    def _is_fixed_raw_github(self, line: str) -> bool:
        refs = [m.group("ref") for m in self.RAW_GITHUB_REF.finditer(line)]
        return bool(refs) and all(self.FIXED_REF.search(ref) for ref in refs)

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()

            if stripped.startswith("#"):
                continue

            # Only what is fetched as source: SRC_URI, continuation lines too
            if context.owner_base(line_num) == "SRC_URI":
                for pattern in self.UNRELIABLE_HOSTS:
                    if pattern.search(stripped):
                        if (pattern is self.RAW_GITHUB
                                and self._is_fixed_raw_github(stripped)):
                            break
                        results.append(self.create_result(
                            file=context,
                            line=line_num,
                            message="Download from potentially unreliable hosting service",
                            context=stripped[:60],
                            hint="Use official release URLs and configure MIRRORS",
                        ))
                        break
        
        return results
