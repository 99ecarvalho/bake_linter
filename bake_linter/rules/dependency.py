# -*- coding: utf-8 -*-
"""
Dependency-related rules for Yocto recipes.

These rules check for proper dependency declarations.

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

    # Build-time only packages/tools that shouldn't be in RDEPENDS, matched
    # as whole package names (gcc-symlinks is not gcc)
    BUILD_TIME_TOOLS = {
        "cmake", "autoconf", "automake", "libtool", "pkgconfig", "pkg-config",
        "gettext", "meson", "ninja", "gcc", "g++", "clang", "make", "bison",
        "flex", "swig",
    }

    # Packages that legitimately need build tools at run time: test suites
    # run "make check", -dev packages are for building on the target
    DEV_PACKAGE_SUFFIXES = ("-dev", "-staticdev")

    # Overrides that apply the assignment to a build-host variant, where
    # -native runtime dependencies are correct
    HOST_CLASS_OVERRIDES = ("class-native", "class-nativesdk", "class-cross")

    # Recipes whose packages are for the build host, or that collect build
    # tools on purpose (packagegroup-core-buildessential)
    HOST_RECIPE_CLASSES = {"native", "nativesdk", "cross", "crosssdk",
                           "cross-canadian", "packagegroup"}

    def _is_host_recipe(self, context: FileContext) -> bool:
        pn = context.pn
        if (pn.endswith(("-native", "-cross", "-crosssdk"))
                or pn.startswith(("nativesdk-", "packagegroup-"))
                or "-cross-canadian" in pn):
            return True
        return bool(context.inherits & self.HOST_RECIPE_CLASSES)

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        if self._is_host_recipe(context):
            return results

        for assignment in context.structure.assignments:
            if assignment.base != "RDEPENDS" or assignment.flag is not None:
                continue
            # :remove takes packages away; it does not add a dependency
            if "remove" in assignment.overrides:
                continue
            overrides = assignment.overrides
            if any("-ptest" in o or o.endswith(self.DEV_PACKAGE_SUFFIXES)
                   for o in overrides):
                continue
            if any(o in self.HOST_CLASS_OVERRIDES for o in overrides):
                continue

            for token in assignment.value.split():
                if token.endswith("-native"):
                    message = (
                        f"Native package '{token}' in RDEPENDS of a target "
                        "package; native packages run on the build host"
                    )
                elif token in self.BUILD_TIME_TOOLS:
                    message = f"Build-time tool '{token}' should be in DEPENDS, not RDEPENDS"
                else:
                    continue
                line_num = next(
                    (n for n in range(assignment.line, assignment.end_line + 1)
                     if re.search(rf'(?<![\w${{}}+.-]){re.escape(token)}(?![\w+.-])',
                                  context.lines[n - 1])),
                    assignment.line,
                )
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message=message,
                    context=context.lines[line_num - 1].strip()[:60],
                    hint=f"Move '{token}' to DEPENDS",
                ))
                break  # One warning per assignment

        return results


class MissingPkgconfigInheritRule(BaseRule):
    """
    Check for recipes using pkg-config without inherit pkgconfig.
    
    Recipes that use pkg-config should inherit the pkgconfig class
    for proper sysroot and cross-compilation setup.
    
    Exceptions:
    - Recipes with pkgconfig-native in DEPENDS (just need the tool, not cross setup)
    - Native recipes (ending with -native)
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
        re.compile(r'pkgconfig(?!-native)'),  # Exclude pkgconfig-native
        re.compile(r'\.pc\b'),  # .pc file references
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Skip native recipes - they don't need cross-compilation setup
        recipe_name = context.path.stem
        if '-native' in recipe_name or '_native' in recipe_name:
            return results
        
        # Check if already inherits pkgconfig or has pkgconfig-native in DEPENDS
        inherits_pkgconfig = False
        has_pkgconfig_native = False
        uses_pkgconfig = False
        usage_line = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if stripped.startswith("inherit") and "pkgconfig" in stripped:
                inherits_pkgconfig = True
            
            # Check for pkgconfig-native in DEPENDS
            if re.match(r'DEPENDS\s*[+?:]?=', stripped) and 'pkgconfig-native' in stripped:
                has_pkgconfig_native = True
            
            if not uses_pkgconfig:
                for pattern in self.PKG_CONFIG_USAGE:
                    if pattern.search(line):
                        # Don't flag pkgconfig-native references
                        if 'pkgconfig-native' in line:
                            has_pkgconfig_native = True
                            continue
                        uses_pkgconfig = True
                        usage_line = line_num
                        break
        
        # Only flag if uses pkgconfig and doesn't have inherit or pkgconfig-native
        if uses_pkgconfig and not inherits_pkgconfig and not has_pkgconfig_native:
            results.append(self.create_result(
                file=context,
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
                            file=context,
                            line=line_num,
                            message=f"Essential library '{lib}' should be in RDEPENDS, not RRECOMMENDS",
                            context=stripped[:60],
                            hint=f"Move '{lib}' to RDEPENDS as it's required for operation",
                        ))
                        break
        
        return results
