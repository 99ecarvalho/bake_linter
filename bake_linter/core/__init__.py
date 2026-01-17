# -*- coding: utf-8 -*-
"""
Core module for the Bake Linter engine.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from bake_linter.core.models import LintResult, Severity, RuleConfig
from bake_linter.core.registry import RuleRegistry
from bake_linter.core.engine import LintEngine

__all__ = [
    "LintResult",
    "Severity",
    "RuleConfig",
    "RuleRegistry",
    "LintEngine",
]
