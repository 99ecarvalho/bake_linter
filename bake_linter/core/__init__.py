# -*- coding: utf-8 -*-
"""
Core module for the Bake Linter engine.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
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
