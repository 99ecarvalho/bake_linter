# -*- coding: utf-8 -*-
"""
The oelint_release and oelint_extra_machines settings reach oelint-adv.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

import json
import os
import subprocess
from pathlib import Path

from bake_linter.config import LinterConfig
from bake_linter.core.oelint_integration import OelintAdvIntegration

SHIPPED_CONFIG = Path(__file__).parent.parent / "config" / ".bake-linter.yaml"


def test_settings_are_loaded(tmp_path):
    config_file = tmp_path / ".bake-linter.yaml"
    config_file.write_text(
        "settings:\n"
        "  oelint_release: styhead\n"
        "  oelint_extra_machines:\n"
        "    - my-board\n"
        "    - other-board\n"
    )
    config = LinterConfig.load(config_file)
    assert config.oelint_release == "styhead"
    assert config.oelint_extra_machines == ["my-board", "other-board"]


def test_shipped_config_leaves_release_and_machines_unset():
    config = LinterConfig.load(SHIPPED_CONFIG)
    assert config.oelint_release is None
    assert config.oelint_extra_machines == []


def _fake_integration(monkeypatch, seen):
    integration = OelintAdvIntegration()
    monkeypatch.setattr(integration, "is_available", lambda: True)
    monkeypatch.setattr(integration, "get_version", lambda: None)

    def fake_run(args, **kwargs):
        seen["args"] = list(args)
        if "--constantmods" in args:
            path = args[args.index("--constantmods") + 1].lstrip("+")
            seen["constantmods_path"] = path
            with open(path) as f:
                seen["constantmods"] = json.load(f)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(integration, "_run_command", fake_run)
    return integration


def test_release_and_machines_are_passed_and_temp_file_removed(tmp_path, monkeypatch):
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text('SUMMARY = "foo"\n')
    seen = {}
    integration = _fake_integration(monkeypatch, seen)

    integration.run([recipe], release="styhead", extra_machines=["my-board"])

    args = seen["args"]
    assert args[args.index("--release") + 1] == "styhead"
    assert seen["constantmods"] == {"replacements": {"machines": ["my-board"]}}
    assert not os.path.exists(seen["constantmods_path"])


def test_no_options_means_no_extra_arguments(tmp_path, monkeypatch):
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text('SUMMARY = "foo"\n')
    seen = {}
    integration = _fake_integration(monkeypatch, seen)

    integration.run([recipe])

    assert "--release" not in seen["args"]
    assert "--constantmods" not in seen["args"]


def test_no_temp_file_left_when_nothing_to_lint(tmp_path, monkeypatch):
    import tempfile
    seen = {}
    integration = _fake_integration(monkeypatch, seen)
    before = set(Path(tempfile.gettempdir()).glob("oelint-constantmods-*"))

    integration.run([tmp_path], extra_machines=["my-board"])

    after = set(Path(tempfile.gettempdir()).glob("oelint-constantmods-*"))
    assert after == before
    assert "args" not in seen
