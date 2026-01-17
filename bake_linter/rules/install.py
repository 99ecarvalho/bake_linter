"""
Install command rules for Yocto recipes.

These rules check for proper file installation patterns in do_install tasks.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class CpInsteadOfInstallRule(BaseRule):
    """
    Check for cp command usage instead of install in do_install.
    
    Using install instead of cp is preferred because:
    - install can set permissions in one command
    - install can create directories
    - install strips binaries when requested
    - Makes permission expectations explicit
    """
    
    rule_id = "INSTALL001"
    name = "Using cp Instead of install"
    description = "Detects cp command usage instead of install in do_install"
    default_severity = Severity.WARNING
    groups = ["install", "best_practices"]
    hint = "Use 'install -m MODE' instead of 'cp' for explicit permissions"

    # Pattern to detect cp commands (but not in comments or strings that are clearly not commands)
    CP_PATTERN = re.compile(r'^\s*cp\s+(?:-[a-zA-Z]+\s+)*')
    
    # Pattern to detect we're in a do_install task
    INSTALL_TASK_PATTERN = re.compile(r'^do_install(?:[_:]|$|\s*\(\))')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_do_install = False
        brace_depth = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            # Track if we're inside do_install
            if self.INSTALL_TASK_PATTERN.match(stripped):
                in_do_install = True
                if '{' in stripped:
                    brace_depth = 1
                continue
            
            # Track brace depth
            if in_do_install:
                brace_depth += stripped.count('{') - stripped.count('}')
                if brace_depth <= 0:
                    in_do_install = False
                    brace_depth = 0
                    continue
                
                # Check for cp command
                if self.CP_PATTERN.match(stripped):
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message="Using 'cp' instead of 'install' command",
                        context=stripped[:60],
                        hint="Use 'install -d' for dirs, 'install -m MODE' for files",
                    ))
        
        return results


class InstallWithoutModeRule(BaseRule):
    """
    Check for install commands without explicit permission mode.
    
    Relying on default umask for permissions can lead to:
    - Inconsistent file permissions across builds
    - Security issues from overly permissive defaults
    - Unexpected behavior in different build environments
    """
    
    rule_id = "INSTALL002"
    name = "Install Without Explicit Mode"
    description = "Detects install commands without explicit -m permission mode"
    default_severity = Severity.WARNING
    groups = ["install", "security"]
    hint = "Add '-m 0755' for binaries, '-m 0644' for data files"

    # Pattern to detect install command (not install -d which doesn't need -m)
    # Looking for install commands that copy files (not just -d for directory)
    INSTALL_PATTERN = re.compile(r'^\s*install\s+')
    
    # Pattern to detect -d flag (directory creation, doesn't need -m)
    DIR_FLAG_PATTERN = re.compile(r'\s-d\s')
    
    # Pattern to detect -m flag (handles various valid forms):
    # -m 0644, -m0644, -Dm 0644, -Dm0644, -D -m 0644, etc.
    MODE_FLAG_PATTERN = re.compile(r'-[A-Za-z]*m\s*[0-7]{3,4}')
    
    # Pattern to detect we're in a do_install task
    INSTALL_TASK_PATTERN = re.compile(r'^do_install(?:[_:]|$|\s*\(\))')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_do_install = False
        brace_depth = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            # Track if we're inside do_install
            if self.INSTALL_TASK_PATTERN.match(stripped):
                in_do_install = True
                if '{' in stripped:
                    brace_depth = 1
                continue
            
            # Track brace depth
            if in_do_install:
                brace_depth += stripped.count('{') - stripped.count('}')
                if brace_depth <= 0:
                    in_do_install = False
                    brace_depth = 0
                    continue
                
                # Check for install command without -m (but not -d only)
                if self.INSTALL_PATTERN.match(stripped):
                    # Skip if it's just directory creation (-d flag present, no source files)
                    if self.DIR_FLAG_PATTERN.search(stripped):
                        # Check if there are source files after -d (install -d dir is ok, install -d -m ... src dst needs -m)
                        # Simple heuristic: if -d is the only flag before ${D}, it's just dir creation
                        if stripped.count('${D}') == 1 and not self.MODE_FLAG_PATTERN.search(stripped):
                            continue
                    
                    # Check if -m flag is present
                    if not self.MODE_FLAG_PATTERN.search(stripped):
                        # Skip pure directory creation
                        if self.DIR_FLAG_PATTERN.search(stripped) and stripped.count('$') <= 2:
                            continue
                        
                        results.append(self.create_result(
                            file=context.path,
                            line=line_num,
                            message="install command without explicit -m permission mode",
                            context=stripped[:60],
                            hint="Add -m 0755 for executables, -m 0644 for data files",
                        ))
        
        return results


class MkdirInsteadOfInstallDRule(BaseRule):
    """
    Check for mkdir -p usage instead of install -d in do_install.
    
    Using install -d is preferred because:
    - Sets consistent ownership and permissions
    - Standard Yocto/OE practice
    - More explicit about intent
    """
    
    rule_id = "INSTALL003"
    name = "mkdir Instead of install -d"
    description = "Detects mkdir -p usage instead of install -d in do_install"
    default_severity = Severity.INFO
    groups = ["install", "best_practices"]
    hint = "Use 'install -d' instead of 'mkdir -p'"

    MKDIR_PATTERN = re.compile(r'^\s*mkdir\s+(?:-p\s+)?')
    INSTALL_TASK_PATTERN = re.compile(r'^do_install(?:[_:]|$|\s*\(\))')

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
                
                if self.MKDIR_PATTERN.match(stripped):
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message="Using 'mkdir' instead of 'install -d'",
                        context=stripped[:60],
                        hint="Replace 'mkdir -p' with 'install -d' for consistency",
                    ))
        
        return results


class UsrLocalInstallRule(BaseRule):
    """
    Check for installations to /usr/local which is non-standard for Yocto.
    
    /usr/local is inappropriate for Yocto builds because:
    - Conflicts with package management
    - Not part of standard Yocto FHS
    - May cause rootfs inconsistencies
    """
    
    rule_id = "INSTALL004"
    name = "Installation to /usr/local"
    description = "Detects installations to /usr/local which is non-standard for Yocto"
    default_severity = Severity.ERROR
    groups = ["install", "portability"]
    hint = "Use ${bindir}, ${libdir}, ${datadir} instead of /usr/local/*"

    USR_LOCAL_PATTERN = re.compile(r'/usr/local(?:/|$)')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if self.USR_LOCAL_PATTERN.search(line):
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message="Installation to /usr/local is non-standard for Yocto",
                    context=stripped[:60],
                    hint="Use standard variables: ${bindir}, ${libdir}, ${datadir}",
                ))
        
        return results


class NonFHSPathRule(BaseRule):
    """
    Check for installations outside standard FHS paths.
    
    Detects files installed to non-standard locations that may cause:
    - Package management issues
    - Portability problems
    - Maintenance difficulties
    """
    
    rule_id = "INSTALL005"
    name = "Non-FHS Installation Path"
    description = "Detects files installed outside standard FHS paths"
    default_severity = Severity.INFO
    groups = ["install", "portability"]
    hint = "Use standard paths: ${bindir}, ${libdir}, ${datadir}, ${sysconfdir}"

    # Standard FHS paths (as variables or literals)
    STANDARD_PATHS = [
        r'\$\{D\}\$\{bindir\}',
        r'\$\{D\}\$\{sbindir\}',
        r'\$\{D\}\$\{libdir\}',
        r'\$\{D\}\$\{libexecdir\}',
        r'\$\{D\}\$\{datadir\}',
        r'\$\{D\}\$\{sysconfdir\}',
        r'\$\{D\}\$\{localstatedir\}',
        r'\$\{D\}\$\{includedir\}',
        r'\$\{D\}\$\{docdir\}',
        r'\$\{D\}\$\{mandir\}',
        r'\$\{D\}\$\{infodir\}',
        r'\$\{D\}\$\{systemd_system_unitdir\}',
        r'\$\{D\}\$\{systemd_user_unitdir\}',
        r'\$\{D\}/usr/',
        r'\$\{D\}/etc/',
        r'\$\{D\}/var/',
        r'\$\{D\}/opt/',
        r'\$\{D\}/lib/',
        r'\$\{D\}/run/',
        r'\$\{D\}/srv/',
        r'\$\{D\}/home/',
    ]
    
    STANDARD_PATTERN = re.compile('|'.join(STANDARD_PATHS))
    INSTALL_TASK_PATTERN = re.compile(r'^do_install(?:[_:]|$|\s*\(\))')
    INSTALL_PATTERN = re.compile(r'^\s*install\s+.*\$\{D\}(/\S+)')

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
                
                # Check for install commands with non-standard destinations
                if 'install ' in stripped and '${D}' in stripped:
                    # Skip if using standard paths
                    if self.STANDARD_PATTERN.search(stripped):
                        continue
                    
                    # Extract the destination path
                    match = self.INSTALL_PATTERN.search(stripped)
                    if match:
                        dest_path = match.group(1)
                        # Only flag truly unusual paths
                        if not any(p in dest_path for p in ['/usr', '/etc', '/var', '/opt', '/lib', '/run']):
                            results.append(self.create_result(
                                file=context.path,
                                line=line_num,
                                message=f"Installation to non-FHS path: {dest_path}",
                                context=stripped[:60],
                                hint="Consider using standard FHS paths",
                            ))
        
        return results

