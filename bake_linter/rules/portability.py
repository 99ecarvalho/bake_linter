"""
Portability rules for Yocto recipes.

These rules check for issues that affect cross-compilation and
portability across different architectures and build hosts.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class HardcodedCpuFlagsRule(BaseRule):
    """
    Check for hardcoded CPU architecture flags.
    
    Hardcoding -march, -mtune, or similar flags breaks cross-compilation
    and machine independence. Use tune file settings instead.
    """
    
    rule_id = "PORT001"
    name = "Hardcoded CPU Architecture Flags"
    description = "Detects hardcoded -march/-mtune/etc. in compiler flags"
    default_severity = Severity.WARNING
    groups = ["portability", "cross-compile"]
    hint = "Use TUNE_CCARGS or machine/tune configuration instead"

    CPU_FLAG_PATTERNS = [
        re.compile(r'-march=\w+'),
        re.compile(r'-mtune=\w+'),
        re.compile(r'-mcpu=\w+'),
        re.compile(r'-mfpu=\w+'),
        re.compile(r'-mfloat-abi=\w+'),
        re.compile(r'-mabi=\w+'),
        re.compile(r'-m32\b'),
        re.compile(r'-m64\b'),
    ]
    
    FLAG_VARIABLES = ['CFLAGS', 'CXXFLAGS', 'TARGET_CFLAGS', 'TARGET_CXXFLAGS',
                      'EXTRA_OECMAKE', 'EXTRA_OECONF', 'EXTRA_OEMAKE']

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Check if this line modifies flag variables
            is_flag_var = any(var in stripped for var in self.FLAG_VARIABLES)
            
            if is_flag_var:
                for pattern in self.CPU_FLAG_PATTERNS:
                    match = pattern.search(stripped)
                    if match:
                        results.append(self.create_result(
                            file=context.path,
                            line=line_num,
                            message=f"Hardcoded CPU flag: {match.group()}",
                            context=stripped[:60],
                            hint="Let tune files control CPU-specific flags",
                        ))
                        break  # One warning per line
        
        return results


class AbsoluteHostPathRule(BaseRule):
    """
    Check for absolute host filesystem paths in recipes.
    
    Absolute paths like /usr/lib or /home/user break sysroot isolation
    and cause cross-compilation failures.
    
    Excludes documentation variables (SUMMARY, DESCRIPTION, etc.) which
    may contain path-like strings as descriptive text.
    """
    
    rule_id = "PORT002"
    name = "Absolute Host Paths"
    description = "Detects absolute host filesystem paths in recipes"
    default_severity = Severity.ERROR
    groups = ["portability", "cross-compile", "sysroot"]
    hint = "Use Yocto variables like ${STAGING_DIR_TARGET} instead"

    # Host paths that should never appear in recipes
    HOST_PATH_PATTERNS = [
        re.compile(r'["\s=]/usr/include\b'),
        re.compile(r'["\s=]/usr/lib(?:32|64)?\b'),
        re.compile(r'["\s=]/usr/local\b'),
        re.compile(r'["\s=]/lib(?:32|64)?\b(?!/firmware)'),  # Allow /lib/firmware
        re.compile(r'["\s=]/opt\b'),
        re.compile(r'["\s=]/home/\w+'),
        re.compile(r'["\s=]/root/'),
        re.compile(r'["\s=]/etc\b(?!/init\.d)'),  # Allow /etc/init.d in install
    ]
    
    # Contexts where host paths are acceptable
    ACCEPTABLE_CONTEXTS = [
        'TOOLCHAIN_HOST_TASK',
        'SYSROOT_DIRS_NATIVE',
        'HOST_',  # Any HOST_* variables
        'native.bbclass',
        '-native',
    ]
    
    # Documentation/metadata variables (paths here are just text, not code)
    DOCUMENTATION_VARS = {
        'SUMMARY', 'DESCRIPTION', 'HOMEPAGE', 'BUGTRACKER',
        'AUTHOR', 'MAINTAINER', 'LICENSE', 'SECTION',
    }
    
    # Pattern to detect variable assignment
    VAR_ASSIGN_PATTERN = re.compile(r'^([A-Z][A-Z0-9_]*)\s*[+?:]?=')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_task = False
        is_native = '-native' in str(context.path)
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Skip if this is clearly native recipe context
            if is_native or any(ctx in stripped for ctx in self.ACCEPTABLE_CONTEXTS):
                continue
            
            # Skip documentation/metadata variables (they contain text, not code)
            var_match = self.VAR_ASSIGN_PATTERN.match(stripped)
            if var_match:
                var_name = var_match.group(1)
                if var_name in self.DOCUMENTATION_VARS:
                    continue
            
            # Track task context
            if re.match(r'^(do_\w+|fakeroot\s+do_\w+)\s*\(\)\s*\{', stripped):
                in_task = True
                continue
            
            if in_task and stripped == '}':
                in_task = False
                continue
            
            # Check for host paths
            for pattern in self.HOST_PATH_PATTERNS:
                match = pattern.search(stripped)
                if match:
                    # Skip if referencing ${D}/usr, ${STAGING_DIR}, etc.
                    if '${' in stripped[:stripped.find(match.group())+1]:
                        continue
                    
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message="Absolute host path may break cross-compilation",
                        context=stripped[:60],
                        hint="Use ${D}, ${STAGING_DIR_TARGET}, etc.",
                    ))
                    break
        
        return results


class NonPortableSedRule(BaseRule):
    """
    Check for non-portable sed patterns.
    
    Some sed features are GNU-specific and may not work with BusyBox
    or BSD sed commonly found in target systems.
    """
    
    rule_id = "PORT003"
    name = "Non-Portable Sed Usage"
    description = "Detects GNU-specific sed features"
    default_severity = Severity.INFO
    groups = ["portability", "shell"]
    hint = "Use POSIX-compliant sed for better portability"

    # GNU-specific sed patterns
    GNU_SED_PATTERNS = [
        (re.compile(r'\bsed\s+.*-i(?!\s*"")'), "sed -i without backup suffix (GNU-specific)"),
        (re.compile(r'\bsed\s+.*-r\b'), "sed -r (use -E for extended regex)"),
        (re.compile(r'\bsed\s+.*\\d'), "\\d digit class (use [0-9])"),
        (re.compile(r'\bsed\s+.*\\w'), "\\w word class (use [a-zA-Z0-9_])"),
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_task = False
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Track task context
            if re.match(r'^(do_\w+|fakeroot\s+do_\w+)\s*\(\)\s*\{', stripped):
                in_task = True
                continue
            
            if in_task and stripped == '}':
                in_task = False
                continue
            
            if in_task and 'sed' in stripped:
                for pattern, msg in self.GNU_SED_PATTERNS:
                    if pattern.search(stripped):
                        results.append(self.create_result(
                            file=context.path,
                            line=line_num,
                            message=msg,
                            context=stripped[:60],
                        ))
        
        return results
