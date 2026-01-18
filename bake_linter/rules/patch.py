# -*- coding: utf-8 -*-
"""
Patch-related rules for Yocto recipes.

These rules check for proper patch handling.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class PatchWithoutStriplevelRule(BaseRule):
    """
    Check for patches in SRC_URI without explicit striplevel parameter.
    
    While striplevel=1 is the default, being explicit helps:
    - Document the expected patch format
    - Avoid issues if defaults change
    - Make maintenance easier
    """
    
    rule_id = "PATCH001"
    name = "Patch Without Strip Level"
    description = "Detects patches in SRC_URI without explicit striplevel"
    default_severity = Severity.INFO
    groups = ["patch"]
    hint = "Add ;striplevel=1 (or appropriate level) to patch URI"

    # Pattern to find patches in SRC_URI
    PATCH_PATTERN = re.compile(r'file://[^\s"]+\.(patch|diff)')
    
    # Pattern to check if striplevel is specified
    STRIPLEVEL_PATTERN = re.compile(r';striplevel=\d+')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_src_uri = False
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            # Check if we're in a SRC_URI context
            if 'SRC_URI' in stripped:
                in_src_uri = True
            
            # Look for patches
            if in_src_uri or 'SRC_URI' in stripped:
                matches = self.PATCH_PATTERN.findall(line)
                if matches:
                    # Check each patch reference on this line
                    for patch_match in self.PATCH_PATTERN.finditer(line):
                        patch_uri = patch_match.group(0)
                        # Get the rest of the line after this patch to check for striplevel
                        rest_of_entry = line[patch_match.end():patch_match.end() + 50]
                        
                        # Check if striplevel is specified for this patch
                        if not self.STRIPLEVEL_PATTERN.search(rest_of_entry):
                            # Also check if it's on the same URI (before next file:// or quote)
                            next_separator = min(
                                rest_of_entry.find('file://') if 'file://' in rest_of_entry else 999,
                                rest_of_entry.find('"') if '"' in rest_of_entry else 999,
                                rest_of_entry.find(' \\') if ' \\' in rest_of_entry else 999,
                            )
                            check_area = rest_of_entry[:next_separator] if next_separator < 999 else rest_of_entry
                            
                            if not self.STRIPLEVEL_PATTERN.search(check_area):
                                results.append(self.create_result(
                                    file=context.path,
                                    line=line_num,
                                    message="Patch without explicit striplevel",
                                    context=patch_uri[:50],
                                    hint="Add ;striplevel=1 after patch filename",
                                ))
            
            # End of SRC_URI (no continuation)
            if in_src_uri and not stripped.endswith('\\') and '"' in stripped:
                in_src_uri = False
        
        return results


class SrcrevUnpinnedRule(BaseRule):
    """
    Check for unpinned git SRCREV that causes non-reproducible builds.
    
    SRCREV should be pinned to a specific commit SHA for reproducible builds.
    Using branch names or AUTOREV is dangerous for production.
    
    Note: SRCREV_FORMAT is a special variable used for multi-repo version
    formatting and should not be checked - it's a format string, not a commit.
    """
    
    rule_id = "SRCREV001"
    name = "Unpinned Git SRCREV"
    description = "Detects unpinned git revisions (AUTOREV, branch names)"
    default_severity = Severity.ERROR
    groups = ["variables", "security", "reproducibility"]
    hint = "Pin SRCREV to specific commit hash for production recipes"

    # SHA-1 hash pattern (40 hex chars)
    SHA_PATTERN = re.compile(r'^[a-f0-9]{40}$')
    
    # Pattern to match SRCREV variable assignments
    # Captures the suffix (empty, _reponame, _FORMAT, etc.) and the value
    SRCREV_PATTERN = re.compile(r'^SRCREV(_[\w]+)?\s*[?:]?=\s*["\']?([^"\']+)["\']?')
    
    # Dangerous SRCREV values
    DANGEROUS_VALUES = [
        '${AUTOREV}',
        'AUTOREV',
        'master',
        'main',
        'HEAD',
        'develop',
        'dev',
        'trunk',
    ]
    
    # Special SRCREV suffixes that are NOT commit hashes
    # SRCREV_FORMAT is a format string for multi-repo SRCPV generation
    SPECIAL_SUFFIXES = ['_FORMAT']
    
    # Pattern for recipe names that are expected to track HEAD
    DEV_RECIPE_PATTERN = re.compile(r'[-_](git|dev|snapshot|trunk|tip)\.bb$')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Skip development recipes that are expected to use AUTOREV
        if self.DEV_RECIPE_PATTERN.search(str(context.path)):
            return results
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            # Look for SRCREV assignments
            match = self.SRCREV_PATTERN.match(stripped)
            if match:
                suffix = match.group(1) or ''  # Could be None, '_FORMAT', '_reponame', etc.
                value = match.group(2).strip()
                
                # Skip special suffixes like SRCREV_FORMAT (format string, not commit)
                if suffix in self.SPECIAL_SUFFIXES:
                    continue
                
                # Check if it's a dangerous value
                if value in self.DANGEROUS_VALUES:
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message=f"Unpinned SRCREV '{value}' causes non-reproducible builds",
                        context=stripped[:60],
                        hint="Pin to specific commit: SRCREV = \"<40-char-sha1>\"",
                    ))
                # Check if it looks like a branch name (not a SHA)
                elif value and not self.SHA_PATTERN.match(value) and not value.startswith('${'):
                    # Could be a branch name
                    if not any(c in value for c in ['$', '{', '}']):
                        results.append(self.create_result(
                            file=context.path,
                            line=line_num,
                            message=f"SRCREV '{value}' appears to be a branch name, not a commit hash",
                            context=stripped[:60],
                            hint="Pin to specific commit: SRCREV = \"<40-char-sha1>\"",
                        ))
        
        return results
