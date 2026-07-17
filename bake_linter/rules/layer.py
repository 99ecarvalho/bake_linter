# -*- coding: utf-8 -*-
"""
Layer configuration rules for Yocto/OpenEmbedded.

These rules check layer.conf files for proper configuration.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class LayerseriesCompatRule(BaseRule):
    """
    Check for valid LAYERSERIES_COMPAT in layer.conf files.
    
    LAYERSERIES_COMPAT declares which Yocto releases the layer supports.
    It should be set with valid release names.
    """
    
    rule_id = "LAYER001"
    name = "LAYERSERIES_COMPAT Validation"
    description = "Verifies LAYERSERIES_COMPAT is set with valid Yocto releases"
    default_severity = Severity.ERROR
    groups = ["layer", "compatibility"]
    hint = "Add valid LAYERSERIES_COMPAT_layername with supported releases"

    # Valid Yocto release names (recent to old)
    VALID_RELEASES = [
        'styhead', 'scarthgap', 'nanbield', 'mickledore', 'langdale',
        'kirkstone', 'honister', 'hardknott', 'gatesgarth', 'dunfell',
        'zeus', 'warrior', 'thud', 'sumo', 'rocko', 'pyro', 'morty',
        'krogoth', 'jethro', 'fido', 'dizzy', 'daisy', 'dora',
    ]
    
    LAYERSERIES_PATTERN = re.compile(r'^LAYERSERIES_COMPAT_(\w+)\s*=\s*["\']([^"\']*)["\']')
    LAYER_COLLECTION_PATTERN = re.compile(r'^BBFILE_COLLECTIONS\s*\+?=\s*["\'](\w+)["\']')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Only check layer.conf files
        if not str(context.path).endswith('layer.conf'):
            return results
        
        layer_name = None
        layerseries_line = 0
        layerseries_value = None
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Find layer collection name
            match = self.LAYER_COLLECTION_PATTERN.match(stripped)
            if match:
                layer_name = match.group(1)
            
            # Find LAYERSERIES_COMPAT
            match = self.LAYERSERIES_PATTERN.match(stripped)
            if match:
                layerseries_line = line_num
                layerseries_value = match.group(2)
        
        # Check if LAYERSERIES_COMPAT is missing
        if layer_name and not layerseries_value:
            results.append(self.create_result(
                file=context,
                line=1,
                message=f"Missing LAYERSERIES_COMPAT_{layer_name}",
                hint=f'Add: LAYERSERIES_COMPAT_{layer_name} = "kirkstone langdale mickledore nanbield scarthgap"',
            ))
            return results
        
        # Validate release names
        if layerseries_value:
            releases = layerseries_value.split()
            invalid_releases = [r for r in releases if r not in self.VALID_RELEASES]
            
            if invalid_releases:
                results.append(self.create_result(
                    file=context,
                    line=layerseries_line,
                    message=f"Invalid Yocto release names: {', '.join(invalid_releases)}",
                    hint="Use valid release names: kirkstone, langdale, mickledore, etc.",
                ))
            
            if not releases:
                results.append(self.create_result(
                    file=context,
                    line=layerseries_line,
                    message="LAYERSERIES_COMPAT is empty",
                    hint="Add supported Yocto release names",
                ))
        
        return results
