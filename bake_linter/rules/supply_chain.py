"""
Supply chain and reproducibility rules for Yocto recipes.

These rules check for source integrity and reproducibility issues.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class UnpinnedBranchRule(BaseRule):
    """
    Check for mutable branch references in git URIs.
    
    Even with pinned SRCREV, using development branches like master/main
    makes the source lineage less clear and can cause confusion.
    """
    
    rule_id = "REPRO001"
    name = "Unpinned Branch Usage"
    description = "Detects mutable branch references (master, main, develop) in git URIs"
    default_severity = Severity.WARNING
    groups = ["reproducibility", "source"]
    hint = "Use stable/release branches instead of development branches"

    # Mutable development branches to flag
    MUTABLE_BRANCHES = ['master', 'main', 'develop', 'trunk', 'dev', 'development']
    
    GIT_URI_PATTERN = re.compile(r'(?:git|gitsm)://[^;]+;[^"\']*branch=([^;"\'\s]+)')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            matches = self.GIT_URI_PATTERN.findall(line)
            for branch in matches:
                if branch.lower() in self.MUTABLE_BRANCHES:
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message=f"Mutable branch '{branch}' used in git URI",
                        context=stripped[:60],
                        hint="Use stable/release branches (e.g., stable-2.0, release-1.x)",
                    ))
        
        return results


class MissingLicenseChecksumInBbappendRule(BaseRule):
    """
    Check for bbappend files adding sources without license verification.
    
    When adding new source files via bbappend, the license should be
    verified to ensure compatibility with the base recipe.
    """
    
    rule_id = "SUPPLY001"
    name = "Missing License Verification in bbappend"
    description = "Detects .bbappend adding sources without LIC_FILES_CHKSUM update"
    default_severity = Severity.WARNING
    groups = ["security", "license", "bbappend"]
    hint = "Verify license compatibility when adding new sources"
    
    applicable_file_types = {"bbappend"}

    SRC_URI_MODIFY_PATTERN = re.compile(r'SRC_URI\s*[+:]?=')
    LIC_FILES_PATTERN = re.compile(r'LIC_FILES_CHKSUM')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        if not str(context.path).endswith('.bbappend'):
            return results
        
        modifies_src_uri = False
        has_lic_check = False
        src_uri_line = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if self.SRC_URI_MODIFY_PATTERN.search(stripped):
                modifies_src_uri = True
                if src_uri_line == 0:
                    src_uri_line = line_num
            
            if self.LIC_FILES_PATTERN.search(stripped):
                has_lic_check = True
        
        if modifies_src_uri and not has_lic_check:
            results.append(self.create_result(
                file=context.path,
                line=src_uri_line,
                message="bbappend modifies SRC_URI without updating LIC_FILES_CHKSUM",
                hint="Verify added sources have compatible licenses",
            ))
        
        return results


class UnreliableHostingRule(BaseRule):
    """
    Check for downloads from unreliable or temporary hosting services.
    
    Personal hosting, file sharing sites, and raw GitHub content have
    high disappearance risk and are not suitable for production builds.
    """
    
    rule_id = "SUPPLY002"
    name = "Unreliable Download Hosting"
    description = "Detects downloads from personal/temporary hosting services"
    default_severity = Severity.WARNING
    groups = ["security", "supply_chain", "source"]
    hint = "Use official release sources and configure MIRRORS for fallback"

    # Unreliable hosting patterns
    UNRELIABLE_HOSTS = [
        re.compile(r'dropbox\.com'),
        re.compile(r'drive\.google\.com'),
        re.compile(r'pastebin\.com'),
        re.compile(r'dl\.dropboxusercontent\.com'),
        re.compile(r'raw\.githubusercontent\.com'),
        re.compile(r'gist\.github\.com'),
        re.compile(r'mediafire\.com'),
        re.compile(r'mega\.nz'),
        re.compile(r'sendspace\.com'),
        re.compile(r'wetransfer\.com'),
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if 'SRC_URI' in stripped or 'http' in stripped.lower():
                for pattern in self.UNRELIABLE_HOSTS:
                    if pattern.search(stripped):
                        results.append(self.create_result(
                            file=context.path,
                            line=line_num,
                            message="Download from potentially unreliable hosting service",
                            context=stripped[:60],
                            hint="Use official release URLs and configure MIRRORS",
                        ))
                        break
        
        return results
