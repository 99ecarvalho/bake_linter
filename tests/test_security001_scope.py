# -*- coding: utf-8 -*-
"""
SECURITY001 checks what bitbake fetches, not documentation URLs.

HOMEPAGE, BUGTRACKER and the like only document a URL. In MIRRORS and
PREMIRRORS only the replacement of each (regex, replacement) pair is
fetched, and a git replacement inherits the original URL's parameters.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.security import InsecureUriRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return InsecureUriRule().check(context)


@pytest.mark.parametrize("line", [
    'HOMEPAGE = "http://www.example.org/foo"',
    'BUGTRACKER = "http://bugs.example.org/"',
    'SUMMARY = "Driver for Foo <http://www.example.org>"',
    'UPSTREAM_CHECK_URI = "http://ftp.example.org/releases/"',
    'DISTRO_PN_ALIAS:pn-foo = "OSPDT upstream=http://foo.example.org/"',
    'RECIPE_MAINTAINER:pn-foo = "Jane Doe <jane@example.org> http://example.org"',
    'LICENSE_URL = "http://example.org/license.html"',
])
def test_informational_variable_is_ignored(line):
    assert _check(line + "\n") == []


def test_continued_description_is_ignored():
    content = (
        'DESCRIPTION = "Foo implements the \\\n'
        '    http://example.org/ protocol."\n'
    )
    assert _check(content) == []


@pytest.mark.parametrize("content", [
    'SRC_URI = "http://example.org/foo-${PV}.tar.gz"\n',
    'SRC_URI = "git://example.org/foo.git;branch=main"\n',
    'SRC_URI = "git://example.org/foo.git;protocol=git;branch=main"\n',
    'SRC_URI = "file://a.patch \\\n    ftp://example.org/foo.tar.gz \\\n"\n',
    'do_fetch_extra() {\n    wget http://example.org/foo\n}\n',
])
def test_plaintext_fetch_is_reported(content):
    assert len(_check(content)) == 1


def test_mirror_pattern_is_not_checked():
    content = 'PREMIRRORS:prepend = "http://example.org/.* https://mirror.example.org/foo/ \\n"\n'
    assert _check(content) == []


def test_mirror_http_replacement_is_reported():
    content = (
        'MIRRORS += "\\\n'
        '    https://example.org/.* http://mirror.example.org/foo/ \\n \\\n'
        '"\n'
    )
    results = _check(content)
    assert len(results) == 1
    assert results[0].line == 2
    assert "HTTP" in results[0].message


def test_mirror_git_replacement_inherits_protocol():
    content = 'PREMIRRORS:prepend = "git://example.org/.* git://mirror.example.org/git/ \\n"\n'
    assert _check(content) == []


def test_mirror_git_replacement_with_plaintext_protocol_is_reported():
    content = 'MIRRORS += "git://.*/.* git://mirror.example.org/git/;protocol=git \\n"\n'
    assert len(_check(content)) == 1
