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
                        file=context.path,
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
                        file=context.path,
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
                                file=context.path,
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
                        file=context.path,
                        line=line_num,
                        message="SUID/SGID binary detected - security review needed",
                        context=stripped[:60],
                        hint="Add # SECURITY: justification comment or remove setuid/setgid",
                    ))
        
        return results
