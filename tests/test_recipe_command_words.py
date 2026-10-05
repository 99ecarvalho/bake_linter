# -*- coding: utf-8 -*-
"""
Tests for splitting a shell command in a task into words.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

import pytest

from bake_linter.core.recipe import command_words


@pytest.mark.parametrize("text,words", [
    ('sed -i "s,@A@,${A}," ${D}${sysconfdir}/a.conf',
     ["sed", "-i", "s,@A@,${A},", "${D}${sysconfdir}/a.conf"]),
    ("cp -R a b; rm c", ["cp", "-R", "a", "b"]),
    ("cp a b && echo done", ["cp", "a", "b"]),
    ("cp a b | tee log", ["cp", "a", "b"]),
    ("install -m 0644 a ${D}/b 2>/dev/null", ["install", "-m", "0644", "a", "${D}/b"]),
    ("sed -e s/a/b/ x > y", ["sed", "-e", "s/a/b/", "x"]),
    ('cmd "a;b" c', ["cmd", "a;b", "c"]),
    ("echo 'unbalanced", ["echo", "'unbalanced"]),
])
def test_command_words(text, words):
    assert command_words(text) == words
