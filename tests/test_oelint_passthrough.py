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


def test_failed_run_is_not_reported_as_clean(tmp_path, monkeypatch):
    """With --exit-zero, a non-zero exit means oelint-adv itself failed; its
    stderr is a traceback, not a list of findings."""
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text('SUMMARY = "foo"\n')
    integration = OelintAdvIntegration()
    monkeypatch.setattr(integration, "is_available", lambda: True)
    monkeypatch.setattr(
        integration, "_run_command",
        lambda args, **kw: subprocess.CompletedProcess(
            args, 1, "", "Traceback ...\nModuleNotFoundError: No module named 'oelint_parser'\n"
        ),
    )

    results, summary, _stdout, stderr = integration.run([recipe])

    assert results == []
    assert summary is None
    assert "oelint_parser" in stderr


def test_cli_exits_with_runtime_error_when_oelint_fails(tmp_path, monkeypatch):
    from bake_linter import cli
    from bake_linter.core.models import ExitCode

    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text('SUMMARY = "foo"\nLICENSE = "MIT"\n')

    def failing(*args, **kwargs):
        raise cli.OelintFailedError("oelint-adv failed (exit code 1): boom")

    monkeypatch.setattr(cli, "run_oelint_adv", failing)

    assert cli.main(["--quiet", str(recipe)]) == ExitCode.RUNTIME_ERROR
