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
                # ${PN}-... is a package of this target recipe, whatever its
                # name ends with (${PN}-modules-protocol-native)
                if token.endswith("-native") and not token.startswith("${PN}-"):
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

    # A run of the pkg-config tool: the command, ${PKG_CONFIG} or $PKG_CONFIG,
    # or the variables pkg-config reads to find .pc files. "pkgconfig" and
    # ".pc" are not: ${libdir}/pkgconfig is just the directory .pc files
    # are installed into, which every library recipe touches.
    PKG_CONFIG_USAGE = re.compile(
        r'(?<![\w${}/.-])(?:pkg-config|\$\{?PKG_CONFIG\}?|'
        r'PKG_CONFIG_(?:PATH|LIBDIR|SYSROOT_DIR))(?![\w-])'
    )
    # URLs and file names may contain "pkg-config" (crate://.../pkg-config/,
    # file://0001-use-pkg-config.patch)
    URI_TOKEN = re.compile(r'\b[a-z][a-z0-9+.-]*://\S+')
    SHELL_COMMENT = re.compile(r'(?:^|\s)#.*$')

    # Variables whose values name packages, files or URLs, or document the
    # recipe, rather than run commands
    NON_COMMAND_VARIABLES = {
        "SUMMARY", "DESCRIPTION", "HOMEPAGE", "FILES", "DEPENDS", "RDEPENDS",
        "RRECOMMENDS", "RSUGGESTS", "RPROVIDES", "RCONFLICTS", "RREPLACES",
        "SRC_URI", "RECIPE_MAINTAINER", "DISTRO_PN_ALIAS",
    }

    def _usage_line(self, context: FileContext) -> int:
        """First line that runs pkg-config, or 0."""
        for line_num, line in enumerate(context.lines, start=1):
            owner = context.owner_base(line_num)
            if owner == "#" or owner in self.NON_COMMAND_VARIABLES:
                continue
            if owner.startswith("PREFERRED_PROVIDER_"):
                continue
            text = self.URI_TOKEN.sub(" ", line)
            if owner.startswith("FUNC:"):
                text = self.SHELL_COMMENT.sub("", text)
            if self.PKG_CONFIG_USAGE.search(text):
                return line_num
        return 0

    @staticmethod
    def _depends_on_pkgconfig_native(structures) -> bool:
        return any(
            a.base == "DEPENDS" and "remove" not in a.overrides
            and "pkgconfig-native" in a.value.split()
            for structure in structures for a in structure.assignments
        )

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        # Skip native recipes - they don't need cross-compilation setup
        recipe_name = context.path.stem
        if '-native' in recipe_name or '_native' in recipe_name:
            return results

        usage_line = self._usage_line(context)
        if not usage_line:
            return results

        # The inherit or the DEPENDS may come from a required .inc; when one
        # cannot be found, what it sets is unknown
        included = context.included_files
        if included is None:
            return results
        inherits_pkgconfig = "pkgconfig" in context.inherits
        has_pkgconfig_native = self._depends_on_pkgconfig_native(
            [context.structure] + [i.structure for i in included])

        # Only flag if uses pkgconfig and doesn't have inherit or pkgconfig-native
        if not inherits_pkgconfig and not has_pkgconfig_native:
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

    # Libraries that are typically essential (not optional), matched as
    # whole package names (glibc-thread-db is not glibc)
    ESSENTIAL_PACKAGES = {
        "libssl", "libcrypto", "libpthread", "librt", "libdl", "libm", "libc",
        "glibc", "musl", "libstdc++", "libgcc", "zlib",
    }

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        # The packages in the value only: the variable name may carry an
        # override such as :libc-glibc
        for assignment in context.structure.assignments:
            if assignment.base != "RRECOMMENDS" or assignment.flag is not None:
                continue
            if "remove" in assignment.overrides:
                continue
            lib = next((t for t in assignment.value.split()
                        if t in self.ESSENTIAL_PACKAGES), None)
            if lib is None:
                continue
            line_num = next(
                (n for n in range(assignment.line, assignment.end_line + 1)
                 if lib in context.lines[n - 1].split("=", 1)[-1].replace('"', " ").split()),
                assignment.line,
            )
            results.append(self.create_result(
                file=context,
                line=line_num,
                message=f"Essential library '{lib}' should be in RDEPENDS, not RRECOMMENDS",
                context=context.lines[line_num - 1].strip()[:60],
                hint=f"Move '{lib}' to RDEPENDS as it's required for operation",
            ))

        return results
