# -*- coding: utf-8 -*-
"""
Bake Linter - Static analysis for BitBake recipes.

A modular, extensible linting framework for validating BitBake recipes,
suitable for CI integration and local developer use.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

__version__ = "1.0.0"
__author__ = "Eduardo Correia <ecorreia@apliant.com.br>"

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
