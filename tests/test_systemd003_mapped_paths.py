# -*- coding: utf-8 -*-
"""
SYSTEMD003 leaves lines that map a literal systemd path to the variable.

Build systems often install units below a literal /usr/lib/systemd; a
recipe that compares that path with ${systemd_unitdir} or moves the files
from it to ${systemd_system_unitdir} is fixing the layout, not
hardcoding it.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext, Severity
from bake_linter.rules.systemd import SystemdHardcodedPathsRule


def _check(body):
    content = 'do_install:append() {\n' + body + '}\n'
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return SystemdHardcodedPathsRule().check(context)


@pytest.mark.parametrize("body", [
    '    if [ "${systemd_unitdir}" != "/usr/lib/systemd" ]; then\n',
    '    mv ${D}/usr/lib/systemd/system/* ${D}${systemd_system_unitdir}/\n',
    '    mv ${D}${prefix}/lib/systemd `dirname ${D}${systemd_unitdir}`\n',
    '    mv ${D}/usr/lib/systemd/user/* ${D}${systemd_user_unitdir}/\n',
])
def test_mapping_not_flagged(body):
    assert _check(body) == []


def test_hardcoded_destination_flagged_as_warning():
    results = _check('    install -d ${D}/usr/lib/systemd/system\n')
    assert len(results) == 1
    assert results[0].severity == Severity.WARNING
