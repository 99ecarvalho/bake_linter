"""
Dependency-related rules for Yocto recipes.

These rules check for proper dependency declarations.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class WrongDependencyTypeRule(BaseRule):
    """
    Check for build-time tools incorrectly placed in RDEPENDS.
    
    Build-time only tools like *-native packages, cmake, autoconf, etc.
    should be in DEPENDS, not RDEPENDS (runtime dependencies).
    """
    
    rule_id = "DEPENDENCY001"
    name = "Wrong Dependency Type"
    description = "Detects build-time tools incorrectly in RDEPENDS"
    default_severity = Severity.WARNING
    groups = ["dependency"]
    hint = "Move build-time tools to DEPENDS"

    # Build-time only packages/tools that shouldn't be in RDEPENDS
    BUILD_TIME_PATTERNS = [
        re.compile(r'\b\S+-native\b'),  # Any -native package
        re.compile(r'\bcmake\b'),
        re.compile(r'\bautoconf\b'),
        re.compile(r'\bautomake\b'),
        re.compile(r'\blibtool\b'),
        re.compile(r'\bpkgconfig\b'),
        re.compile(r'\bpkg-config\b'),
        re.compile(r'\bgettext\b'),
        re.compile(r'\bmeson\b'),
        re.compile(r'\bninja\b'),
        re.compile(r'\bgcc\b'),
        re.compile(r'\bg\+\+\b'),
        re.compile(r'\bclang\b'),
        re.compile(r'\bmake\b'),
        re.compile(r'\bbison\b'),
        re.compile(r'\bflex\b'),
        re.compile(r'\bswig\b'),
    ]
    
    # Pattern to match RDEPENDS assignments
    RDEPENDS_PATTERN = re.compile(r'^RDEPENDS[_:]')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            # Check RDEPENDS lines
            if self.RDEPENDS_PATTERN.match(stripped):
                for pattern in self.BUILD_TIME_PATTERNS:
                    match = pattern.search(stripped)
                    if match:
                        tool = match.group(0)
                        results.append(self.create_result(
                            file=context.path,
                            line=line_num,
                            message=f"Build-time tool '{tool}' should be in DEPENDS, not RDEPENDS",
                            context=stripped[:60],
                            hint=f"Move '{tool}' to DEPENDS",
                        ))
                        break  # One warning per line
        
        return results
