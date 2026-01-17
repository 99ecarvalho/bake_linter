"""
Security-related lint rules for Yocto recipes.

These rules check for potential security issues in BitBake recipes.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class InsecureUriRule(BaseRule):
    """
    Check for insecure URIs in SRC_URI.
    
    Using unencrypted protocols can lead to man-in-the-middle attacks
    during the build process:
    - HTTP instead of HTTPS
    - FTP instead of HTTPS/FTPS
    - git:// instead of https://
    """
    
    rule_id = "SECURITY001"
    name = "Insecure URI"
    description = "Check for insecure URI protocols (HTTP, FTP, git://)"
    default_severity = Severity.WARNING
    groups = ["security", "network"]
    hint = "Use https:// instead of insecure protocols"

    # Pattern for HTTP (excluding localhost and private networks)
    HTTP_PATTERN = re.compile(r'http://(?!localhost|127\.|192\.168\.|10\.)')
    
    # Pattern for unencrypted FTP
    FTP_PATTERN = re.compile(r'ftp://(?!localhost|127\.|192\.168\.|10\.)')
    
    # Pattern for unencrypted git protocol
    GIT_PROTOCOL_PATTERN = re.compile(r'git://(?!localhost|127\.|192\.168\.|10\.)')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Check for HTTP
            if self.HTTP_PATTERN.search(line):
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message="Insecure HTTP URI detected; use HTTPS instead",
                    context=stripped[:80],
                    hint="Change http:// to https://",
                ))
            # Check for FTP
            elif self.FTP_PATTERN.search(line):
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message="Insecure FTP URI detected; use HTTPS or FTPS instead",
                    context=stripped[:80],
                    hint="Change ftp:// to https:// or ftps://",
                ))
            # Check for git:// protocol
            elif self.GIT_PROTOCOL_PATTERN.search(line):
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message="Insecure git:// protocol; use https:// for git repos",
                    context=stripped[:80],
                    hint="Change git://github.com to https://github.com",
                ))
        
        return results


class NoChecksumRule(BaseRule):
    """
    Check that SRC_URI entries have checksums.
    
    Remote files should have SRC_URI[md5sum] and SRC_URI[sha256sum]
    to verify integrity.
    """
    
    rule_id = "SECURITY002"
    name = "Missing Checksum"
    description = "Check for missing checksums on SRC_URI entries"
    default_severity = Severity.WARNING
    groups = ["security", "integrity"]
    hint = "Add SRC_URI[sha256sum] = \"...\" for file integrity verification"
    applicable_file_types = {"recipe"}

    # URI schemes that should have checksums
    CHECKSUM_SCHEMES = {"http", "https", "ftp", "s3"}

    def check(self, context: FileContext) -> List[LintResult]:
        if not self.is_applicable(context):
            return []
        
        results = []
        
        # Check if SRC_URI exists and has remote files
        if "SRC_URI" not in context.variables:
            return []
        
        has_remote = False
        for assignment in context.variables["SRC_URI"]:
            for scheme in self.CHECKSUM_SCHEMES:
                if f"{scheme}://" in assignment.value:
                    has_remote = True
                    break
        
        if not has_remote:
            return []
        
        # Check for checksum variables
        has_checksum = False
        for line in context.lines:
            if "SRC_URI[" in line and ("sha256sum]" in line or "md5sum]" in line):
                has_checksum = True
                break
        
        if not has_checksum:
            results.append(self.create_result(
                file=context.path,
                message="SRC_URI has remote files but no checksums defined",
            ))
        
        return results


class InsecurePermissionsRule(BaseRule):
    """
    Check for overly permissive file permissions.
    """
    
    rule_id = "SECURITY003"
    name = "Insecure Permissions"
    description = "Check for overly permissive file permissions"
    default_severity = Severity.WARNING
    groups = ["security"]

    # Patterns for overly permissive permissions
    INSECURE_PATTERNS = [
        (re.compile(r'chmod\s+777'), "chmod 777 is overly permissive"),
        (re.compile(r'chmod\s+666'), "chmod 666 allows world-write access"),
        (re.compile(r'chmod\s+-R\s+777'), "Recursive chmod 777 is dangerous"),
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            for pattern, message in self.INSECURE_PATTERNS:
                if pattern.search(line):
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message=message,
                        context=stripped[:60],
                        hint="Use more restrictive permissions (e.g., 755 or 644)",
                    ))
        
        return results


class HardcodedCredentialsRule(BaseRule):
    """
    Check for potential hardcoded credentials or secrets.
    """
    
    rule_id = "SECURITY004"
    name = "Hardcoded Credentials"
    description = "Check for potential hardcoded credentials or secrets"
    default_severity = Severity.ERROR
    groups = ["security", "credentials"]
    hint = "Use environment variables or secure credential storage instead of hardcoding"

    # Patterns that might indicate hardcoded credentials
    CREDENTIAL_PATTERNS = [
        (re.compile(r'password\s*=\s*["\'][^"\']+["\']', re.I), "Possible hardcoded password"),
        (re.compile(r'api[_-]?key\s*=\s*["\'][^"\']+["\']', re.I), "Possible hardcoded API key"),
        (re.compile(r'secret\s*=\s*["\'][^"\']+["\']', re.I), "Possible hardcoded secret"),
        (re.compile(r'token\s*=\s*["\'][a-zA-Z0-9]{20,}["\']', re.I), "Possible hardcoded token"),
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            for pattern, message in self.CREDENTIAL_PATTERNS:
                if pattern.search(line):
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message=message,
                        # Don't include the actual line content to avoid logging credentials
                        hint=self.hint,
                    ))
                    break  # One warning per line
        
        return results
