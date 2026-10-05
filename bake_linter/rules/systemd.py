# -*- coding: utf-8 -*-
"""
Systemd-specific rules for Yocto recipes.

These rules check for proper systemd integration patterns.

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


class SystemdWithoutInheritRule(BaseRule):
    """
    Check for systemd usage without inherit systemd.

    Using the systemd class's packaging variables (SYSTEMD_SERVICE,
    SYSTEMD_AUTO_ENABLE, SYSTEMD_PACKAGES) without inheriting the systemd
    class will cause build failures or unexpected behavior.

    Note: systemd_unitdir/systemd_system_unitdir/systemd_user_unitdir are
    NOT included here - they're plain FHS path variables exported directly
    by bitbake.conf (meta/conf/bitbake.conf), available regardless of
    'inherit systemd'. A recipe can use those paths to manually install
    files without ever touching the systemd class.

    Note: This rule only applies to .bb files. .bbappend files inherit
    everything from their base recipe, including inherit statements.
    """

    rule_id = "SYSTEMD001"
    name = "Systemd Usage Without Inherit"
    description = "Detects usage of systemd class packaging variables without inherit systemd"
    default_severity = Severity.ERROR
    groups = ["systemd"]
    hint = "Add 'inherit systemd' before using systemd features"

    # Systemd-related patterns that require inherit systemd
    SYSTEMD_PATTERNS = [
        re.compile(r'^SYSTEMD_SERVICE[_:]'),
        re.compile(r'^SYSTEMD_AUTO_ENABLE[_:]'),
        re.compile(r'^SYSTEMD_PACKAGES\s*[+?]?='),
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Skip .bbappend files - they inherit from their base recipe
        # The base recipe is responsible for 'inherit systemd'
        file_path = str(context.path)
        if file_path.endswith('.bbappend'):
            return results
        
        # Skip .inc files - they are included by other recipes
        # which handle the inherit statement
        if file_path.endswith('.inc'):
            return results
        
        # The class may be inherited in a required file, or through an inline
        # expression (inherit ${@bb.utils.contains(..., 'systemd', '', d)})
        if "systemd" in context.inherits:
            return results
        # An include that cannot be found may inherit it
        if context.included_files is None:
            return results
        
        # Look for systemd usage without inherit
        for a in context.structure.assignments:
            if a.flag:
                continue
            stripped = context.lines[a.line - 1].strip()
            if not any(p.search(stripped) for p in self.SYSTEMD_PATTERNS):
                continue
            # SYSTEMD_SERVICE:${PN} = "" turns the class's handling off
            if not a.value.strip():
                continue
            results.append(self.create_result(
                file=context,
                line=a.line,
                message="Systemd feature used without 'inherit systemd'",
                context=stripped[:70],
                hint="Add 'inherit systemd' to use systemd features",
            ))
        
        return results


class SystemdMissingServiceDeclarationRule(BaseRule):
    """
    Check for systemd service files installed without SYSTEMD_SERVICE declaration.
    
    When installing .service files, SYSTEMD_SERVICE:${PN} should be declared
    to properly integrate with the systemd class.
    """
    
    rule_id = "SYSTEMD002"
    name = "Missing SYSTEMD_SERVICE Declaration"
    description = "Detects .service files installed without SYSTEMD_SERVICE declaration"
    default_severity = Severity.ERROR
    groups = ["systemd"]
    hint = "Add SYSTEMD_SERVICE:${PN} = \"service-name.service\""

    # Pattern to find .service file installations
    SERVICE_INSTALL_PATTERN = re.compile(
        r'install\s+.*?([a-zA-Z0-9_-]+\.service)\s+\$\{D\}'
    )
    
    # Pattern to find SYSTEMD_SERVICE declaration
    SERVICE_DECL_PATTERN = re.compile(r'^SYSTEMD_SERVICE[_:]')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # First, check if recipe inherits systemd, here or in a required file
        if "systemd" not in context.inherits:
            return results  # SYSTEMD001 will catch this
        # SYSTEMD_SERVICE may be declared in an include that cannot be found
        included = context.included_files
        if included is None:
            return results
        
        # Collect installed service files
        installed_services = []
        service_install_lines = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            
            match = self.SERVICE_INSTALL_PATTERN.search(stripped)
            if match:
                service_name = match.group(1)
                installed_services.append(service_name)
                service_install_lines.append((line_num, service_name))
        
        if not installed_services:
            return results
        
        # Check for SYSTEMD_SERVICE declaration
        has_service_decl = False
        declared_services = []
        
        structures = [context.structure] + [i.structure for i in included]
        for a in (a for s in structures for a in s.assignments):
            if self.SERVICE_DECL_PATTERN.match(a.name):
                has_service_decl = True
                declared_services.extend(a.value.split())
        
        if not has_service_decl:
            for line_num, service_name in service_install_lines:
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message=f"Service '{service_name}' installed without SYSTEMD_SERVICE declaration",
                    hint=f"Add: SYSTEMD_SERVICE:${{PN}} = \"{service_name}\"",
                ))
        
        return results


class SystemdHardcodedPathsRule(BaseRule):
    """
    Check for hardcoded systemd paths instead of BitBake variables.
    
    Hardcoded paths like /lib/systemd/system should use ${systemd_system_unitdir}
    for portability across different distributions.
    
    Note: Only DESTINATION paths need variables. Source paths (SRC_URI, ${WORKDIR})
    can use literal paths since they refer to file locations in the build workspace.
    """
    
    rule_id = "SYSTEMD003"
    name = "Hardcoded Systemd Paths"
    description = "Detects hardcoded systemd paths instead of using variables"
    default_severity = Severity.WARNING
    groups = ["systemd", "portability"]

    # Hardcoded paths and their variable replacements
    HARDCODED_PATHS = [
        (re.compile(r'/lib/systemd/system(?![a-z])'), "${systemd_system_unitdir}"),
        (re.compile(r'/usr/lib/systemd/system(?![a-z])'), "${systemd_system_unitdir}"),
        (re.compile(r'/etc/systemd/system(?![a-z])'), "${sysconfdir}/systemd/system"),
        (re.compile(r'/lib/systemd/user(?![a-z])'), "${systemd_user_unitdir}"),
        (re.compile(r'/usr/lib/systemd/user(?![a-z])'), "${systemd_user_unitdir}"),
        (re.compile(r'/lib/systemd(?![a-z/])'), "${systemd_unitdir}"),
        (re.compile(r'/usr/lib/systemd(?![a-z/])'), "${systemd_unitdir}"),
    ]

    UNITDIR_VARIABLE_PATTERN = re.compile(
        r'\$\{systemd_(?:unitdir|system_unitdir|user_unitdir)\}')

    # Patterns indicating the line is a SOURCE path context (not a destination)
    SOURCE_PATH_PATTERNS = [
        re.compile(r'^\s*SRC_URI\s*[+?]?='),           # SRC_URI assignment
        re.compile(r'^\s*SRC_URI\s*:'),                # SRC_URI with override
        re.compile(r'file://'),                        # file:// URI (source file location)
        re.compile(r'\$\{WORKDIR\}/.*/systemd/'),      # ${WORKDIR}/path - source location
        re.compile(r'\$\{S\}/.*/systemd/'),            # ${S}/path - source location
        re.compile(r'\$\{UNPACKDIR\}/.*/systemd/'),    # ${UNPACKDIR}/path - source location
    ]

    # Patterns for FILES variable contexts (handled by STYLE011 instead)
    FILES_PATTERNS = [
        re.compile(r'^\s*FILES[_:]'),                   # FILES:${PN} = or FILES_${PN} =
        re.compile(r'^\s*FILES\s*[+?]?='),             # FILES = or FILES +=
    ]

    # Patterns for image inspection contexts (validation/QA code, not installation)
    # These scan already-built images and need literal paths
    IMAGE_INSPECTION_PATTERNS = [
        re.compile(r'\$\{IMAGE_ROOTFS\}'),             # Inspecting built image
        re.compile(r'\$\{DEPLOY_DIR'),                 # Inspecting deploy directory
        re.compile(r'\$\{IMGDEPLOYDIR\}'),             # Image deploy directory
    ]

    # Commands used for inspection/validation (not installation)
    INSPECTION_COMMANDS = re.compile(
        r'\b(find|grep|ls|cat|test|check|validate|scan|inspect|read|stat|file)\b'
    )

    # Pattern to detect install commands with proper destination
    # e.g., "install ... ${WORKDIR}/path/file ${D}${systemd_system_unitdir}"
    INSTALL_WITH_PROPER_DEST = re.compile(
        r'install\s+.*\$\{(WORKDIR|S|UNPACKDIR)\}/.*/systemd/.*\s+\$\{D\}\$\{systemd_'
    )

    def _is_source_path_context(self, line: str) -> bool:
        """Check if the line is in a source path context (not a destination)."""
        for pattern in self.SOURCE_PATH_PATTERNS:
            if pattern.search(line):
                return True
        
        # Check for install command with source from WORKDIR and proper destination
        if self.INSTALL_WITH_PROPER_DEST.search(line):
            return True
        
        return False

    def _is_files_variable_context(self, line: str) -> bool:
        """Check if the line is a FILES variable assignment.
        
        FILES variable contexts are handled by STYLE011 with INFO severity
        since hardcoded paths in FILES work correctly but are not ideal style.
        """
        for pattern in self.FILES_PATTERNS:
            if pattern.search(line):
                return True
        return False

    def _is_image_inspection_context(self, line: str) -> bool:
        """Check if the line is inspecting an already-built image.
        
        Image inspection code (ROOTFS_POSTPROCESS_COMMAND, QA checks, etc.)
        needs to scan actual filesystem paths in the built image. Using
        literal paths is appropriate here since:
        - The image is already built
        - Files are in their final locations
        - We need literal paths to find/grep/inspect them
        
        Examples:
            find ${IMAGE_ROOTFS}/usr/lib/systemd/system -name "*.service"
            grep -r "something" ${IMAGE_ROOTFS}/etc/systemd/system
        """
        # Check for image rootfs variables
        for pattern in self.IMAGE_INSPECTION_PATTERNS:
            if pattern.search(line):
                return True
        
        return False

    def _is_hardcoded_destination(self, line: str) -> bool:
        """
        Check if the hardcoded path is used as a DESTINATION (which is bad).
        
        Bad: install -d ${D}/usr/lib/systemd/system
        Bad: install file ${D}/usr/lib/systemd/system/
        Good: install file ${D}${systemd_system_unitdir}
        """
        # Check for ${D}/ followed by hardcoded systemd path (bad destination)
        if re.search(r'\$\{D\}/(usr/)?lib/systemd/', line):
            return True
        
        # Check for install -d with hardcoded path after ${D}
        if re.search(r'install\s+-[dDm0-9]*\s+\$\{D\}/(usr/)?lib/systemd', line):
            return True
        
        return False

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Track if we're inside a multi-line SRC_URI or FILES variable
        in_src_uri = False
        in_files_var = False
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            # Track multi-line SRC_URI blocks
            if re.match(r'^\s*SRC_URI\s*[+?:]?=', line):
                in_src_uri = True
            if in_src_uri:
                # SRC_URI continues if line ends with \ or we're in a quoted string
                if not stripped.endswith('\\') and (stripped.endswith('"') or stripped.endswith("'")):
                    in_src_uri = False
                # Skip - SRC_URI paths are source file locations
                continue
            
            # Track multi-line FILES variable blocks (handled by STYLE011)
            if self._is_files_variable_context(line):
                in_files_var = True
            if in_files_var:
                # FILES continues if line ends with \ or we're in a quoted string
                if not stripped.endswith('\\') and (stripped.endswith('"') or stripped.endswith("'")):
                    in_files_var = False
                # Skip - FILES paths are style concerns, not errors (STYLE011)
                continue
            
            # Skip source path contexts (file://, ${WORKDIR}, etc.)
            if self._is_source_path_context(line):
                continue
            
            # Skip image inspection contexts (${IMAGE_ROOTFS}, find/grep commands)
            # These scan already-built images and need literal paths
            if self._is_image_inspection_context(line):
                continue
            
            # A line that also uses the variable compares the literal path
            # with it or moves files from the literal path to it: the
            # build system installed there, the recipe is mapping it
            if self.UNITDIR_VARIABLE_PATTERN.search(line):
                continue
            
            # Check for hardcoded paths
            for pattern, replacement in self.HARDCODED_PATHS:
                if pattern.search(line):
                    # Only flag if it's clearly a destination path issue
                    # or not in any recognized source context
                    if self._is_hardcoded_destination(line) or not self._is_source_path_context(line):
                        results.append(self.create_result(
                            file=context,
                            line=line_num,
                            message="Hardcoded systemd path found",
                            context=stripped[:70],
                            hint=f"Use {replacement} instead",
                        ))
                    break  # One warning per line
        
        return results
