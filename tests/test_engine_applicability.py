# -*- coding: utf-8 -*-
"""
The engine runs a rule only on the kinds of file it declares.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from bake_linter.core.engine import LintEngine
from bake_linter.core.registry import get_registry


def test_rule_does_not_run_on_other_file_types(tmp_path, monkeypatch):
    """A rule whose check() does not test the file type itself is still
    only run on the types it declares."""
    from bake_linter.core.models import LintResult, Severity
    from bake_linter.rules.base import BaseRule

    class BbappendOnly(BaseRule):
        rule_id = "TEST001"
        name = "test"
        description = "test"
        applicable_file_types = {"bbappend"}

        def check(self, context):
            return [LintResult(rule_id=self.rule_id, file=context.path,
                               severity=Severity.WARNING, message="ran")]

    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text('SUMMARY = "foo"\n')
    append = tmp_path / "foo_%.bbappend"
    append.write_text('SUMMARY = "foo"\n')

    engine = LintEngine()
    monkeypatch.setattr(engine, "_get_enabled_rules", lambda: [BbappendOnly()])

    assert [r.file.name for r in engine.lint_files([recipe, append])] == ["foo_%.bbappend"]


def test_recipe_only_rule_runs_on_recipes(tmp_path):
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text('SUMMARY = "foo"\n')

    engine = LintEngine()
    engine.configure(enabled_rules=["LICENSE001"])

    assert [r.rule_id for r in engine.lint_files([recipe])] == ["LICENSE001"]


def test_declared_file_types_exist():
    known = {"recipe", "bbappend", "include"}
    registry = get_registry()
    registry.discover_rules()
    for rule_id, rule_cls in registry.get_all_rules().items():
        assert rule_cls.applicable_file_types <= known, rule_id
