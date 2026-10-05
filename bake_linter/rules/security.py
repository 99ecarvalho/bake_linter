# -*- coding: utf-8 -*-
"""
Security-related lint rules for Yocto recipes.

These rules check for potential security issues in BitBake recipes.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class InsecureUriRule(BaseRule):
    """
    Check for insecure URIs in SRC_URI.
    
    Using unencrypted protocols can lead to man-in-the-middle attacks
    during the build process:
    - HTTP instead of HTTPS
    - FTP instead of HTTPS/FTPS
    - a git fetch whose effective transport is the plaintext git daemon

    Note ``git://`` alone is NOT insecure: in a bitbake SRC_URI it is the
    *fetcher scheme* (as is ``gitsm://``), and the wire protocol comes from
    the ``;protocol=`` parameter. ``git://host/repo;protocol=ssh`` transports
    over SSH; a missing parameter, or ``git``, ``http`` or ``rsync``, is
    plaintext. Each git URI on a line is checked on its own.
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
    
    # A git or gitsm fetch URI, up to the end of its parameters
    GIT_URI_PATTERN = re.compile(
        r'\bgit(?:sm)?://(?!localhost|127\.|192\.168\.|10\.)[^"\'\s\\]*'
    )
    GIT_PROTOCOL_PARAM = re.compile(r';protocol=([^;"\'\s\\]+)')

    # The transport of a bitbake git fetch comes from the ";protocol="
    # parameter, not from the scheme (fetch2/git.py urldata_init:
    # "if 'protocol' in ud.parm: ud.proto = ud.parm['protocol']"). Poky
    # overwhelmingly writes git://...;protocol=https, so the scheme by itself
    # says nothing about security. Without the parameter bitbake falls back to
    # the plaintext git daemon protocol; git, http and rsync are plaintext too.
    GIT_SECURE_PROTOCOLS = {"ssh", "https", "file"}

    # Variables that only document a URL; bitbake never fetches from them
    INFORMATIONAL_VARIABLES = {
        "HOMEPAGE", "BUGTRACKER", "SUMMARY", "DESCRIPTION", "DISTRO_PN_ALIAS",
        "UPSTREAM_CHECK_URI", "RECIPE_MAINTAINER", "LICENSE_URL",
    }

    # MIRRORS and PREMIRRORS hold (regex, replacement) pairs. Only the
    # replacement is fetched from; the regex just matches the original URL.
    MIRROR_VARIABLES = {"MIRRORS", "PREMIRRORS"}

    def _insecure_git_message(self, line: str, require_protocol: bool = True) -> Optional[str]:
        """Why the first insecure git/gitsm URI on *line* is insecure, if any."""
        for match in self.GIT_URI_PATTERN.finditer(line):
            uri = match.group(0)
            scheme = uri.split("://", 1)[0]
            protocol = self.GIT_PROTOCOL_PARAM.search(uri)
            if protocol is None:
                if not require_protocol:
                    continue
                return (
                    f"{scheme}:// fetch has no ;protocol= parameter, so it "
                    "falls back to the plaintext git daemon protocol"
                )
            if protocol.group(1) not in self.GIT_SECURE_PROTOCOLS:
                return (
                    f"{scheme}:// fetch uses the plaintext "
                    f";protocol={protocol.group(1)} transport"
                )
        return None

    def _finding(self, text: str, require_protocol: bool = True) -> Optional[Tuple[str, str]]:
        """(message, hint) for the first insecure URI in *text*, if any."""
        if self.HTTP_PATTERN.search(text):
            return ("Insecure HTTP URI detected; use HTTPS instead",
                    "Change http:// to https://")
        if self.FTP_PATTERN.search(text):
            return ("Insecure FTP URI detected; use HTTPS or FTPS instead",
                    "Change ftp:// to https:// or ftps://")
        # A git fetch on a plaintext transport. An explicit
        # ;protocol=ssh/https/file is secure.
        message = self._insecure_git_message(text, require_protocol)
        if message:
            return (message,
                    "Use ;protocol=https (or ;protocol=ssh for a private repo)")
        return None

    def _check_mirrors(self, context: FileContext, assignment) -> List[LintResult]:
        """Check the replacement of each (regex, replacement) pair. A git
        replacement needs no ;protocol= of its own: fetch2 uri_replace
        carries the original URL's parameters over to it."""
        results = []
        tokens = assignment.value.replace("\\n", " ").split()
        for replacement in tokens[1::2]:
            finding = self._finding(replacement, require_protocol=False)
            if not finding:
                continue
            line_num = next(
                (n for n in range(assignment.line, assignment.end_line + 1)
                 if replacement in context.lines[n - 1]),
                assignment.line,
            )
            message, hint = finding
            results.append(self.create_result(
                file=context,
                line=line_num,
                message=message,
                context=context.lines[line_num - 1].strip()[:80],
                hint=hint,
            ))
        return results

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        for assignment in context.structure.assignments:
            if assignment.base in self.MIRROR_VARIABLES:
                results.extend(self._check_mirrors(context, assignment))

        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()

            if stripped.startswith("#"):
                continue

            # Documentation URLs are never fetched; mirrors are checked
            # above as pairs
            owner = context.owner_base(line_num)
            if owner in self.INFORMATIONAL_VARIABLES or owner in self.MIRROR_VARIABLES:
                continue

            finding = self._finding(line)
            if finding:
                message, hint = finding
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message=message,
                    context=stripped[:80],
                    hint=hint,
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
                file=context,
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
                        file=context,
                        line=line_num,
                        message=message,
                        context=stripped[:60],
                        hint="Use more restrictive permissions (e.g., 755 or 644)",
                    ))
        
        return results


class HardcodedCredentialsRule(BaseRule):
    """
    Check for potential hardcoded credentials or secrets.
    
    IMPORTANT: This rule skips contexts where credential-like words appear
    but are not actual credentials:
    - LICENSE variables (package names may contain 'password')
    - SUMMARY/DESCRIPTION (documentation text)
    - SRC_URI (package names in URLs)
    - Comments
    - Placeholder patterns (@PASSWORD@, ${PASSWORD}, etc.)
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
    
    # Variables where credential-like words are expected/safe (metadata, not code)
    SAFE_VARIABLE_PREFIXES = [
        'LICENSE',      # Package names may contain 'password' (passport-oauth2-client-password)
        'SUMMARY',      # Documentation text
        'DESCRIPTION',  # Documentation text
        'HOMEPAGE',     # URLs
        'BUGTRACKER',   # URLs
        'CVE_PRODUCT',  # Product names
    ]
    
    # Placeholder patterns that indicate intentional variable substitution
    PLACEHOLDER_PATTERNS = [
        re.compile(r'@[A-Z_]+@'),          # @PASSWORD@, @API_KEY@
        re.compile(r'\$\{[A-Z_]+\}'),      # ${PASSWORD}, ${API_KEY}
        re.compile(r'\$[A-Z_]+'),          # $PASSWORD
        re.compile(r'<[A-Z_]+>'),          # <PASSWORD>
        re.compile(r'\[\[[A-Z_]+\]\]'),    # [[PASSWORD]]
    ]

    def _is_safe_context(self, line: str) -> bool:
        """Check if the line is in a safe context where credential words are expected."""
        stripped = line.strip()
        
        # Check for safe variable prefixes (LICENSE:${PN}-package-password = "MIT")
        for prefix in self.SAFE_VARIABLE_PREFIXES:
            if stripped.startswith(prefix):
                return True
            # Also check for override syntax: LICENSE:${PN}-foo
            if re.match(rf'^{prefix}[_:]', stripped):
                return True
        
        # Check for SRC_URI (package names in URLs may contain 'password')
        if 'SRC_URI' in line:
            return True
        
        return False

    def _contains_placeholder(self, line: str) -> bool:
        """Check if the line contains placeholder patterns."""
        for pattern in self.PLACEHOLDER_PATTERNS:
            if pattern.search(line):
                return True
        return False

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            # Skip safe contexts (LICENSE, SUMMARY, DESCRIPTION, SRC_URI)
            if self._is_safe_context(line):
                continue
            
            # Skip lines with placeholder patterns
            if self._contains_placeholder(line):
                continue
            
            for pattern, message in self.CREDENTIAL_PATTERNS:
                if pattern.search(line):
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message=message,
                        # Don't include the actual line content to avoid logging credentials
                        hint=self.hint,
                    ))
                    break  # One warning per line
        
        return results


class DangerousRmRfRule(BaseRule):
    """
    Check for potentially dangerous rm -rf usage.
    
    rm -rf with unguarded variables can delete unintended files
    if the variable is empty or set to /.
    """
    
    rule_id = "SECURITY005"
    name = "Dangerous rm -rf Usage"
    description = "Detects rm -rf with potentially dangerous patterns"
    default_severity = Severity.ERROR
    groups = ["security"]
    hint = "Add guards to verify variables are set before rm -rf"

    # Dangerous rm patterns
    DANGEROUS_PATTERNS = [
        re.compile(r'rm\s+-rf?\s+/\s'),  # rm -rf /
        re.compile(r'rm\s+-rf?\s+/\*'),  # rm -rf /*
        re.compile(r'rm\s+-rf?\s+\$\{D\}/\*'),  # rm -rf ${D}/*
        re.compile(r'rm\s+-rf?\s+\$\{D\}\$\{[^}]+\}/\*'),  # rm -rf ${D}${VAR}/*
    ]
    
    # Pattern to check for unguarded variable deletion
    UNGUARDED_PATTERN = re.compile(r'rm\s+-rf?\s+\$\{D\}\$\{([^}]+)\}')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            for pattern in self.DANGEROUS_PATTERNS:
                if pattern.search(stripped):
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message="Potentially dangerous rm -rf pattern",
                        context=stripped[:60],
                        hint="Add guards: [ -n \"${VAR}\" ] && rm -rf ...",
                    ))
                    break
        
        return results


class EvalUsageRule(BaseRule):
    """
    Check for eval usage in shell tasks.
    
    eval can lead to code injection if used with untrusted input.
    """
    
    rule_id = "SECURITY006"
    name = "eval Usage in Shell"
    description = "Detects eval usage which can lead to code injection"
    default_severity = Severity.WARNING
    groups = ["security"]
    hint = "Avoid eval; use direct command execution"

    EVAL_PATTERN = re.compile(r'^\s*eval\s+')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_shell_task = False
        brace_depth = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Detect shell function start (not python)
            if re.match(r'^do_\w+\s*\(', stripped) and 'python' not in stripped:
                in_shell_task = True
                if '{' in stripped:
                    brace_depth = 1
                continue
            
            if in_shell_task:
                brace_depth += stripped.count('{') - stripped.count('}')
                if brace_depth <= 0:
                    in_shell_task = False
                    brace_depth = 0
                    continue
                
                if self.EVAL_PATTERN.match(stripped):
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message="eval usage can lead to code injection",
                        context=stripped[:60],
                        hint="Use direct command execution instead of eval",
                    ))
        
        return results


class BuildPathLeakageRule(BaseRule):
    """
    Check for build path leakage into runtime files.
    
    References to ${WORKDIR}, ${S}, ${B}, ${TMPDIR}, etc. written into
    installed files will break reproducibility and may expose build 
    system information.
    
    This rule detects when BUILD-TIME variables are being written into
    config files or scripts that will end up on the target filesystem.
    """
    
    rule_id = "SECURITY007"
    name = "Build Path Leakage"
    description = "Detects build paths leaking into runtime configuration"
    default_severity = Severity.WARNING
    groups = ["security", "reproducibility"]
    hint = "Use runtime paths (${datadir}, ${sysconfdir}) not build paths"

    # Build-time variables that should NEVER appear in installed file content
    # These are paths that exist only during build and would be invalid at runtime
    BUILD_TIME_VARS = [
        re.compile(r'\$\{S\}'),           # Source directory
        re.compile(r'\$\{WORKDIR\}'),     # Work directory
        re.compile(r'\$\{B\}'),           # Build directory
        re.compile(r'\$\{TMPDIR\}'),      # Temp directory
        re.compile(r'\$\{STAGING_DIR\}'), # Staging directory
        re.compile(r'\$\{STAGING_INCDIR\}'),
        re.compile(r'\$\{STAGING_LIBDIR\}'),
        re.compile(r'\$\{RECIPE_SYSROOT\}'),
        re.compile(r'\$\{RECIPE_SYSROOT_NATIVE\}'),
    ]
    
    INSTALL_TASK_PATTERN = re.compile(r'^do_install(?:[_:]|$|\s*\(\))')
    
    # Pattern to detect write operations to ${D} (content being written to target)
    WRITE_TO_D_PATTERN = re.compile(r'(echo|printf|cat)\s+.*>.*\$\{D\}|>>.*\$\{D\}|sed\s+-i.*\$\{D\}')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_do_install = False
        brace_depth = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if self.INSTALL_TASK_PATTERN.match(stripped):
                in_do_install = True
                if '{' in stripped:
                    brace_depth = 1
                continue
            
            if in_do_install:
                brace_depth += stripped.count('{') - stripped.count('}')
                if brace_depth <= 0:
                    in_do_install = False
                    brace_depth = 0
                    continue
                
                # Only check lines that write content to ${D} (target filesystem)
                # Look for echo/printf/cat/sed writing to ${D}
                if ('echo' in stripped or 'printf' in stripped or 
                    'cat' in stripped or 'sed' in stripped):
                    # Check if any build-time variable is in the content
                    for pattern in self.BUILD_TIME_VARS:
                        if pattern.search(stripped):
                            results.append(self.create_result(
                                file=context,
                                line=line_num,
                                message="Build path may leak into installed file",
                                context=stripped[:60],
                                hint="Use ${datadir}, ${sysconfdir} instead of build paths",
                            ))
                            break
        
        return results


class SuidSgidBinaryRule(BaseRule):
    """
    Check for SUID/SGID binary installations without justification.
    
    SUID/SGID binaries run with elevated privileges and are security-sensitive.
    They should be explicitly documented/justified.
    """
    
    rule_id = "SECURITY008"
    name = "SUID/SGID Binary Detection"
    description = "Flags SUID/SGID binary installations"
    default_severity = Severity.WARNING
    groups = ["security", "permissions"]
    hint = "Add security review comment or remove SUID/SGID if not necessary"

    # Patterns for SUID/SGID
    SUID_CHMOD_PATTERN = re.compile(r'chmod\s+[46][0-7]{3}\s')
    SGID_CHMOD_PATTERN = re.compile(r'chmod\s+[26][0-7]{3}\s')
    SYMBOLIC_SUID_PATTERN = re.compile(r'chmod\s+[^#]*u\+s')
    SYMBOLIC_SGID_PATTERN = re.compile(r'chmod\s+[^#]*g\+s')
    
    SECURITY_COMMENT_PATTERN = re.compile(r'#.*(?:SECURITY|SUID|SGID|reviewed|justified)', re.IGNORECASE)

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_task = False
        brace_depth = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Track do_install task
            if re.match(r'^(?:fakeroot\s+)?do_install\s*\(\)\s*\{', stripped):
                in_task = True
                brace_depth = 1
                continue
            
            if in_task:
                brace_depth += stripped.count('{') - stripped.count('}')
                if brace_depth <= 0:
                    in_task = False
                    continue
                
                # Skip if has security comment on preceding line
                if line_num > 1:
                    prev_line = context.lines[line_num - 2].strip()
                    if self.SECURITY_COMMENT_PATTERN.search(prev_line):
                        continue
                
                # Check for SUID/SGID patterns
                is_suid_sgid = (
                    self.SUID_CHMOD_PATTERN.search(stripped) or
                    self.SGID_CHMOD_PATTERN.search(stripped) or
                    self.SYMBOLIC_SUID_PATTERN.search(stripped) or
                    self.SYMBOLIC_SGID_PATTERN.search(stripped)
                )
                
                if is_suid_sgid:
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message="SUID/SGID binary detected - security review needed",
                        context=stripped[:60],
                        hint="Add # SECURITY: justification comment or remove setuid/setgid",
                    ))
        
        return results
