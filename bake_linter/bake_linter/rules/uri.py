# -*- coding: utf-8 -*-
"""
URI and source validation rules for Yocto recipes.

These rules check for SRC_URI consistency, protocol usage,
and git revision validity.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from __future__ import annotations

import re
from typing import List, Set, Tuple

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class SrcUriProtocolConsistencyRule(BaseRule):
    """
    Check for consistent protocol usage across SRC_URI entries.
    
    Mixed protocols (http vs https, git vs https) for similar sources
    can indicate inconsistency or security issues.
    """
    
    rule_id = "URI001"
    name = "SRC_URI Protocol Consistency"
    description = "Detects mixed protocol usage across SRC_URI entries"
    default_severity = Severity.INFO
    groups = ["source", "consistency"]
    hint = "Standardize on secure protocols (HTTPS) for consistency"

    GIT_PROTOCOL_PATTERN = re.compile(r'git://[^;]+;[^"\']*protocol=(\w+)')
    HTTP_PATTERN = re.compile(r'https?://[^\s;]+')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        git_protocols: Set[str] = set()
        http_protocols: Set[str] = set()
        src_uri_lines: List[Tuple[int, str]] = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if 'SRC_URI' in stripped or 'git://' in stripped or 'http' in stripped.lower():
                src_uri_lines.append((line_num, stripped))
                
                # Check git protocols
                git_matches = self.GIT_PROTOCOL_PATTERN.findall(stripped)
                git_protocols.update(git_matches)
                
                # Check HTTP vs HTTPS
                if 'http://' in stripped.lower():
                    http_protocols.add('http')
                if 'https://' in stripped.lower():
                    http_protocols.add('https')
        
        # Flag mixed protocols
        if len(git_protocols) > 1:
            results.append(self.create_result(
                file=context.path,
                line=src_uri_lines[0][0] if src_uri_lines else 1,
                message=f"Mixed git protocols used: {', '.join(sorted(git_protocols))}",
                hint="Standardize on protocol=https for all git sources",
            ))
        
        if 'http' in http_protocols and 'https' in http_protocols:
            results.append(self.create_result(
                file=context.path,
                line=src_uri_lines[0][0] if src_uri_lines else 1,
                message="Mixed HTTP and HTTPS protocols in SRC_URI",
                hint="Use HTTPS for all HTTP sources",
            ))
        
        return results


class GitSrcrevValidityRule(BaseRule):
    """
    Check for valid git SRCREV format and consistency.
    
    SRCREV should be a valid 40-character SHA-1 hash or ${AUTOREV}.
    Also checks for SRCREV without git:// URI and vice versa.
    """
    
    rule_id = "URI002"
    name = "Git SRCREV Validity"
    description = "Validates git SRCREV format and git URI consistency"
    default_severity = Severity.WARNING
    groups = ["source", "git"]
    hint = "Use valid 40-character SHA-1 hash for SRCREV"

    SRCREV_PATTERN = re.compile(r'SRCREV\s*=\s*["\']([^"\']+)["\']')
    GIT_URI_PATTERN = re.compile(r'git://|gitsm://')
    VALID_SHA1_PATTERN = re.compile(r'^[a-fA-F0-9]{40}$')
    
    VALID_SRCREV_VALUES = ['${AUTOREV}', 'AUTOINC', 'INVALID']

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        has_git_uri = False
        srcrev_value = None
        srcrev_line = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Check for git URI
            if self.GIT_URI_PATTERN.search(stripped):
                has_git_uri = True
            
            # Check for SRCREV
            match = self.SRCREV_PATTERN.search(stripped)
            if match:
                srcrev_value = match.group(1)
                srcrev_line = line_num
        
        # Validate SRCREV format
        if srcrev_value and srcrev_line:
            # Skip if it's a known valid value
            if srcrev_value in self.VALID_SRCREV_VALUES:
                pass
            elif srcrev_value.startswith('${'):
                # Variable reference, can't validate
                pass
            elif not self.VALID_SHA1_PATTERN.match(srcrev_value):
                results.append(self.create_result(
                    file=context.path,
                    line=srcrev_line,
                    message=f"Invalid SRCREV format: '{srcrev_value[:20]}...'",
                    hint="SRCREV should be 40-character SHA-1 hash or ${AUTOREV}",
                ))
        
        # Check for SRCREV without git URI
        if srcrev_value and not has_git_uri:
            # Only flag if it looks like a real recipe (not .inc)
            if str(context.path).endswith('.bb'):
                results.append(self.create_result(
                    file=context.path,
                    line=srcrev_line,
                    message="SRCREV defined but no git:// URI found",
                    hint="SRCREV is only applicable to git sources",
                ))
        
        return results


class VersionConstraintSyntaxRule(BaseRule):
    """
    Check for valid version constraint syntax in dependencies.
    
    Version constraints should use format: package (>= version)
    with proper parentheses and valid operators.
    """
    
    rule_id = "DEPENDS001"
    name = "Version Constraint Syntax"
    description = "Validates version constraint syntax in DEPENDS/RDEPENDS"
    default_severity = Severity.WARNING
    groups = ["dependency", "syntax"]
    hint = "Use format: package (>= version) with parentheses"

    # Valid operators
    VALID_OPERATORS = ['>=', '>', '=', '<=', '<']
    
    # Pattern for correct syntax: package (operator version)
    CORRECT_PATTERN = re.compile(r'\b[\w${}-]+\s+\((>=|>|=|<=|<)\s+[\d\w.]+\)')
    
    # Patterns for common errors
    MISSING_PARENS = re.compile(r'\b([\w${}-]+)\s+(>=|>|=|<=|<)\s+([\d\w.]+)(?!\))')
    INVALID_OPERATOR = re.compile(r'\b[\w${}-]+\s+\((=>|=<|==|!=)\s+[\d\w.]+\)')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Only check dependency variables
            if not any(var in stripped for var in ['DEPENDS', 'RDEPENDS', 'RRECOMMENDS', 'RSUGGESTS']):
                continue
            
            # Check for missing parentheses
            match = self.MISSING_PARENS.search(stripped)
            if match:
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message=f"Version constraint missing parentheses: {match.group(0)}",
                    context=stripped[:60],
                    hint=f'Use: {match.group(1)} ({match.group(2)} {match.group(3)})',
                ))
            
            # Check for invalid operators
            match = self.INVALID_OPERATOR.search(stripped)
            if match:
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message="Invalid version constraint operator",
                    context=stripped[:60],
                    hint="Valid operators: >=, >, =, <=, <",
                ))
        
        return results
