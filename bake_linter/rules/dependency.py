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


class MissingPkgconfigInheritRule(BaseRule):
    """
    Check for recipes using pkg-config without inherit pkgconfig.
    
    Recipes that use pkg-config should inherit the pkgconfig class
    for proper sysroot and cross-compilation setup.
    """
    
    rule_id = "DEPENDENCY002"
    name = "Missing pkgconfig Inherit"
    description = "Detects recipes using pkg-config without inherit pkgconfig"
    default_severity = Severity.WARNING
    groups = ["dependency", "inherit"]
    hint = "Add 'inherit pkgconfig'"

    PKG_CONFIG_USAGE = [
        re.compile(r'PKG_CONFIG'),
        re.compile(r'pkg-config'),
        re.compile(r'pkgconfig'),
        re.compile(r'\.pc\b'),  # .pc file references
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Check if already inherits pkgconfig
        inherits_pkgconfig = False
        uses_pkgconfig = False
        usage_line = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if stripped.startswith("inherit") and "pkgconfig" in stripped:
                inherits_pkgconfig = True
            
            if not uses_pkgconfig:
                for pattern in self.PKG_CONFIG_USAGE:
                    if pattern.search(line):
                        uses_pkgconfig = True
                        usage_line = line_num
                        break
        
        if uses_pkgconfig and not inherits_pkgconfig:
            results.append(self.create_result(
                file=context.path,
                line=usage_line,
                message="Recipe uses pkg-config but doesn't inherit pkgconfig",
                hint="Add 'inherit pkgconfig' for proper cross-compilation setup",
            ))
        
        return results


class RrecommendsEssentialRule(BaseRule):
    """
    Check for essential dependencies in RRECOMMENDS instead of RDEPENDS.
    
    Essential libraries (like libssl, libc, etc.) should be in RDEPENDS,
    not RRECOMMENDS, as the package won't function without them.
    """
    
    rule_id = "DEPENDENCY003"
    name = "Essential Dependency in RRECOMMENDS"
    description = "Detects essential dependencies incorrectly in RRECOMMENDS"
    default_severity = Severity.WARNING
    groups = ["dependency"]
    hint = "Move essential dependencies to RDEPENDS"

    # Libraries that are typically essential (not optional)
    ESSENTIAL_PATTERNS = [
        re.compile(r'\blibssl\b'),
        re.compile(r'\blibcrypto\b'),
        re.compile(r'\blibpthread\b'),
        re.compile(r'\blibrt\b'),
        re.compile(r'\blibdl\b'),
        re.compile(r'\blibm\b'),
        re.compile(r'\blibc\b'),
        re.compile(r'\bglibc\b'),
        re.compile(r'\bmusl\b'),
        re.compile(r'\blibstdc\+\+\b'),
        re.compile(r'\blibgcc\b'),
        re.compile(r'\bzlib\b'),
    ]
    
    RRECOMMENDS_PATTERN = re.compile(r'^RRECOMMENDS[_:]')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if self.RRECOMMENDS_PATTERN.match(stripped):
                for pattern in self.ESSENTIAL_PATTERNS:
                    match = pattern.search(stripped)
                    if match:
                        lib = match.group(0)
                        results.append(self.create_result(
                            file=context.path,
                            line=line_num,
                            message=f"Essential library '{lib}' should be in RDEPENDS, not RRECOMMENDS",
                            context=stripped[:60],
                            hint=f"Move '{lib}' to RDEPENDS as it's required for operation",
                        ))
                        break
        
        return results
