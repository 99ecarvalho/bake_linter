# -*- coding: utf-8 -*-
"""
Bake Linter - Production-grade linter for Yocto/OpenEmbedded recipes.

A modular, extensible linting framework for validating BitBake recipes,
suitable for CI integration and local developer use.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

__version__ = "1.0.0"
__author__ = "Eduardo Correia"

from bake_linter.core.models import LintResult, Severity, RuleConfig
from bake_linter.core.engine import LintEngine
from bake_linter.core.registry import RuleRegistry

__all__ = [
    "LintResult",
    "Severity", 
    "RuleConfig",
    "LintEngine",
    "RuleRegistry",
    "__version__",
]
