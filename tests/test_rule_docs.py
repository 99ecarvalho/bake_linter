# -*- coding: utf-8 -*-
"""
The rule documentation matches the rule classes.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

import re

import pytest

from bake_linter.core.registry import get_registry
from bake_linter.utils.gen_docs import INDEX_PATH, RULES_DIR, render_index


def _rules():
    registry = get_registry()
    registry.discover_rules()
    return registry.get_all_rules()


def test_rule_index_is_up_to_date():
    text = INDEX_PATH.read_text()
    assert render_index(text, _rules()) == text, (
        "docs/rules/README.md is out of date: run "
        "python -m bake_linter.utils.gen_docs --index"
    )


@pytest.mark.parametrize("rule_id,rule_cls", sorted(_rules().items()))
def test_rule_page_header_matches_the_rule(rule_id, rule_cls):
    page = RULES_DIR / f"{rule_id}.md"
    assert page.is_file(), f"no documentation page for {rule_id}"
    text = page.read_text()

    title = re.search(r"^# (\S+) - (.+)$", text, re.M)
    assert title and title.group(1) == rule_id and title.group(2).strip() == rule_cls.name

    severity = re.search(r"\*\*Severity:\*\*\s*(\w+)", text)
    assert severity and severity.group(1).lower() == rule_cls.default_severity.name.lower()

    enabled = re.search(r"\*\*Enabled by Default:\*\*\s*(\w+)", text)
    expected = "yes" if getattr(rule_cls, "enabled_by_default", True) else "no"
    assert enabled and enabled.group(1).lower() == expected
