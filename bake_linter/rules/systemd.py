"""
Systemd-specific rules for Yocto recipes.

These rules check for proper systemd integration patterns.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class SystemdWithoutInheritRule(BaseRule):
    """
    Check for systemd usage without inherit systemd.
    
    Using systemd variables or paths without inheriting the systemd class
    will cause build failures or unexpected behavior.
    """
    
    rule_id = "SYSTEMD001"
    name = "Systemd Usage Without Inherit"
    description = "Detects usage of systemd variables/paths without inherit systemd"
    default_severity = Severity.ERROR
    groups = ["systemd"]
    hint = "Add 'inherit systemd' before using systemd features"

    # Systemd-related patterns that require inherit systemd
    SYSTEMD_PATTERNS = [
        re.compile(r'\$\{systemd_system_unitdir\}'),
        re.compile(r'\$\{systemd_user_unitdir\}'),
        re.compile(r'\$\{systemd_unitdir\}'),
        re.compile(r'^SYSTEMD_SERVICE[_:]'),
        re.compile(r'^SYSTEMD_AUTO_ENABLE[_:]'),
        re.compile(r'^SYSTEMD_PACKAGES\s*[+?]?='),
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Check if recipe inherits systemd
        inherits_systemd = False
        for line in context.lines:
            stripped = line.strip()
            if stripped.startswith("inherit") and "systemd" in stripped.split():
                inherits_systemd = True
                break
        
        if inherits_systemd:
            return results
        
        # Look for systemd usage without inherit
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            for pattern in self.SYSTEMD_PATTERNS:
                if pattern.search(stripped):
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message="Systemd feature used without 'inherit systemd'",
                        context=stripped[:70],
                        hint="Add 'inherit systemd' to use systemd features",
                    ))
                    break  # One error per line
        
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
        
        # First, check if recipe inherits systemd
        inherits_systemd = False
        for line in context.lines:
            stripped = line.strip()
            if stripped.startswith("inherit") and "systemd" in stripped.split():
                inherits_systemd = True
                break
        
        if not inherits_systemd:
            return results  # SYSTEMD001 will catch this
        
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
        
        for line in context.lines:
            stripped = line.strip()
            if self.SERVICE_DECL_PATTERN.match(stripped):
                has_service_decl = True
                # Extract service names from declaration
                if '=' in stripped:
                    value = stripped.split('=', 1)[1].strip().strip('"\'')
                    declared_services.extend(value.split())
        
        if not has_service_decl:
            for line_num, service_name in service_install_lines:
                results.append(self.create_result(
                    file=context.path,
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
    """
    
    rule_id = "SYSTEMD003"
    name = "Hardcoded Systemd Paths"
    description = "Detects hardcoded systemd paths instead of using variables"
    default_severity = Severity.ERROR
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

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            for pattern, replacement in self.HARDCODED_PATHS:
                if pattern.search(line):
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message=f"Hardcoded systemd path found",
                        context=stripped[:70],
                        hint=f"Use {replacement} instead",
                    ))
                    break  # One warning per line
        
        return results
