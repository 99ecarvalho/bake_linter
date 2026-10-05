# -*- coding: utf-8 -*-
"""
URI and source validation rules for Yocto recipes.

These rules check for SRC_URI consistency, protocol usage,
and git revision validity.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from __future__ import annotations

import re
from typing import Dict, List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class SrcUriProtocolConsistencyRule(BaseRule):
    """
    Check for consistent protocol usage across SRC_URI entries.
    
    Mixed protocols (http vs https, git vs https) for similar sources
    can indicate inconsistency or security issues.
    """
    
    rule_id = "URI001"
    name = "SRC_URI Protocol Consistency"
    description = "Detects mixed protocol usage across SRC_URI entries"
    default_severity = Severity.INFO
    groups = ["source", "consistency"]
    hint = "Standardize on secure protocols (HTTPS) for consistency"

    URI_PATTERN = re.compile(r'^(?P<scheme>[a-z][a-z0-9+.-]*)://', re.I)
    GIT_PROTOCOL_PARAM = re.compile(r';protocol=([^;]+)')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        # Only SRC_URI is fetched; URLs in HOMEPAGE, MIRRORS etc. say nothing
        # about how sources are fetched. Each URI is classified on its own:
        # a git fetch by its ;protocol= (the plaintext git daemon when
        # missing, as in fetch2/git.py), an http(s) fetch by its scheme.
        git_protocols: Dict[str, int] = {}
        http_protocols: Dict[str, int] = {}

        for assignment in context.structure.assignments:
            if assignment.base != "SRC_URI" or assignment.flag is not None:
                continue
            for token in assignment.value.split():
                match = self.URI_PATTERN.match(token)
                if not match:
                    continue
                scheme = match.group("scheme").lower()
                if scheme in ("git", "gitsm"):
                    protocol = self.GIT_PROTOCOL_PARAM.search(token)
                    git_protocols.setdefault(
                        protocol.group(1) if protocol else "git", assignment.line)
                elif scheme in ("http", "https"):
                    http_protocols.setdefault(scheme, assignment.line)

        # Flag mixed protocols
        if len(git_protocols) > 1:
            results.append(self.create_result(
                file=context,
                line=min(git_protocols.values()),
                message=f"Mixed git protocols used: {', '.join(sorted(git_protocols))}",
                hint="Standardize on protocol=https for all git sources",
            ))

        if 'http' in http_protocols and 'https' in http_protocols:
            results.append(self.create_result(
                file=context,
                line=http_protocols['http'],
                message="Mixed HTTP and HTTPS protocols in SRC_URI",
                hint="Use HTTPS for all HTTP sources",
            ))

        return results


class GitSrcrevValidityRule(BaseRule):
    """
    Check for valid git SRCREV format and consistency.
    
    SRCREV should be a valid 40-character SHA-1 hash or ${AUTOREV}.
    Also checks for SRCREV without git:// URI and vice versa.
    """
    
    rule_id = "URI002"
    name = "Git SRCREV Validity"
    description = "Validates git SRCREV format and git URI consistency"
    default_severity = Severity.WARNING
    groups = ["source", "git"]
    hint = "Use valid 40-character SHA-1 hash for SRCREV"

    SRCREV_PATTERN = re.compile(r'SRCREV\s*=\s*["\']([^"\']+)["\']')
    GIT_URI_PATTERN = re.compile(r'git://|gitsm://')
    # SHA-1, or SHA-256 for a repository in git's sha256 object format
    VALID_SHA1_PATTERN = re.compile(r'^(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})$')
    # Other fetchers that use SRCREV, with revisions of their own format
    # (an svn revision number, an hg changeset)
    OTHER_SCM_PATTERN = re.compile(r'\b(?:svn|hg|bzr|repo)://')

    VALID_SRCREV_VALUES = ['${AUTOREV}', 'AUTOINC', 'INVALID']

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        has_git_uri = False
        srcrev_value = None
        srcrev_line = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Check for git URI
            if self.GIT_URI_PATTERN.search(stripped):
                has_git_uri = True
            
            # Check for SRCREV
            match = self.SRCREV_PATTERN.search(stripped)
            if match:
                srcrev_value = match.group(1)
                srcrev_line = line_num
        
        other_scm = any(
            a.base == "SRC_URI" and self.OTHER_SCM_PATTERN.search(a.value)
            for a in context.structure.assignments
        )

        # Validate SRCREV format, as a git commit only when git is the only
        # fetcher it can be for
        if srcrev_value and srcrev_line and has_git_uri and not other_scm:
            # Skip if it's a known valid value
            if srcrev_value in self.VALID_SRCREV_VALUES:
                pass
            elif srcrev_value.startswith('${'):
                # Variable reference, can't validate
                pass
            elif not self.VALID_SHA1_PATTERN.match(srcrev_value):
                results.append(self.create_result(
                    file=context,
                    line=srcrev_line,
                    message=f"Invalid SRCREV format: '{srcrev_value[:20]}...'",
                    hint="SRCREV should be 40-character SHA-1 hash or ${AUTOREV}",
                ))
        
        # Check for SRCREV without git URI. The URI may be in a required
        # file, and svn, hg, bzr and repo fetches use SRCREV too.
        if (srcrev_value and not has_git_uri and not other_scm
                and not context.structure.includes):
            # Only flag if it looks like a real recipe (not .inc)
            if str(context.path).endswith('.bb'):
                results.append(self.create_result(
                    file=context,
                    line=srcrev_line,
                    message="SRCREV defined but no git:// URI found",
                    hint="SRCREV is only applicable to git sources",
                ))
        
        return results


class VersionConstraintSyntaxRule(BaseRule):
    """
    Check for valid version constraint syntax in dependencies.
    
    Version constraints should use format: package (>= version)
    with proper parentheses and valid operators.
    """
    
    rule_id = "DEPENDS001"
    name = "Version Constraint Syntax"
    description = "Validates version constraint syntax in DEPENDS/RDEPENDS"
    default_severity = Severity.WARNING
    groups = ["dependency", "syntax"]
    hint = "Use format: package (>= version) with parentheses"

    # Valid operators
    VALID_OPERATORS = ['>=', '>', '=', '<=', '<']
    
    # Pattern for correct syntax: package (operator version)
    CORRECT_PATTERN = re.compile(r'\b[\w${}-]+\s+\((>=|>|=|<=|<)\s+[\d\w.]+\)')
    
    # Patterns for common errors
    MISSING_PARENS = re.compile(r'\b([\w${}-]+)\s+(>=|>|=|<=|<)\s+([\d\w.]+)(?!\))')
    INVALID_OPERATOR = re.compile(r'\b[\w${}-]+\s+\((=>|=<|==|!=)\s+[\d\w.]+\)')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Only check dependency variables
            if not any(var in stripped for var in ['DEPENDS', 'RDEPENDS', 'RRECOMMENDS', 'RSUGGESTS']):
                continue
            
            # Check for missing parentheses
            match = self.MISSING_PARENS.search(stripped)
            if match:
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message=f"Version constraint missing parentheses: {match.group(0)}",
                    context=stripped[:60],
                    hint=f'Use: {match.group(1)} ({match.group(2)} {match.group(3)})',
                ))
            
            # Check for invalid operators
            match = self.INVALID_OPERATOR.search(stripped)
            if match:
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message="Invalid version constraint operator",
                    context=stripped[:60],
                    hint="Valid operators: >=, >, =, <=, <",
                ))
        
        return results
