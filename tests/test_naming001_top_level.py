# -*- coding: utf-8 -*-
"""
NAMING001 checks only BitBake assignments.

Shell locals in function bodies (under any function header, such as
do_install:append:class-native() or pkg_postinst:${PN} ()), python code
and continuation lines are not BitBake variables, and bitbake.conf itself
defines lowercase names (bindir, prefix, base_libdir, ...).

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.naming import VariableNamingRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(),
    )
    return VariableNamingRule().check(context)


@pytest.mark.parametrize("content", [
    "do_install:append:class-native() {\nfoo=bar\n}\n",
    "pkg_postinst:${PN} () {\nfoo=bar\n}\n",
    "python do_foo() {\nfoo = d.getVar('FOO')\n}\n",
    "def helper(d):\n    foo = 1\n    return foo\n",
    'EXTRA_OECONF = "a \\\nfoo=bar \\\n"\n',
    'FOO = "1"\n    foo = "2"\n',
])
def test_not_bitbake_assignments(content):
    assert _check(content) == []


@pytest.mark.parametrize("name", [
    "bindir", "systemd_unitdir", "base_libdir", "nonarch_base_libdir",
    "prefix", "exec_prefix", "acpaths", "lcl_maybe_fortify",
    "base_bin_progs", "sbin_progs",
])
def test_known_lowercase_names(name):
    assert _check(f'{name} = "x"\n') == []


@pytest.mark.parametrize("line", ['myvar = "x"', 'myvar += "x"', 'myvar =+ "x"', 'myvar ?= "x"'])
def test_recipe_lowercase_variable_is_reported(line):
    assert len(_check(line + "\n")) == 1
