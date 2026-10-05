# -*- coding: utf-8 -*-
"""
PKG002 understands FILES globs the way package.bbclass expands them.

FILES entries go through glob.glob, so '*' and '?' match within one path
component, and a matched directory is packaged with its contents.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.package import FilesNotMatchingInstallRule


def _check(install, files):
    content = (
        'do_install() {\n'
        f'    install -m 0644 foo ${{D}}{install}\n'
        '}\n'
        f'FILES:${{PN}} += "{files}"\n'
    )
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return FilesNotMatchingInstallRule().check(context)


@pytest.mark.parametrize("install,files", [
    ("/opt/foo/libfoo.so", "/opt/foo/*.so"),
    ("/opt/foo-1.0/bin/tool", "/opt/foo*"),
    ("/opt/vendor/bin/tool", "/opt/*/bin"),
    ("/opt/foo/a.conf", "/opt/foo/?.conf"),
    ("/opt/foo/x1", "/opt/foo/x[0-9]"),
    ("/opt/foo/bin/tool", "/opt/foo"),
    ("/opt/foo/bin/tool", "/opt/foo/"),
    ("/opt/foo", "/opt/foo/*.so"),
])
def test_covered(install, files):
    assert _check(install, files) == []


@pytest.mark.parametrize("install,files", [
    ("/opt/foo/libfoo.a", "/opt/foo/*.so"),
    ("/opt/bar/tool", "/opt/foo*"),
    ("/opt/vendor/lib/x", "/opt/*/bin"),
    ("/opt/foo/ab.conf", "/opt/foo/?.conf"),
    ("/opt/foobar", "/opt/foo"),
    # '*' does not cross a '/': /opt/* is /opt/<one component>, which still
    # covers everything below it, but /opt/*.so does not reach /opt/a/b.so
    ("/opt/a/b.so", "/opt/*.so"),
])
def test_not_covered(install, files):
    results = _check(install, files)
    assert len(results) == 1
    assert results[0].rule_id == "PKG002"


@pytest.mark.parametrize("install", ["/opt/foo/lib/x", "/opt/usr/x", "/etcetera/x"])
def test_standard_dir_name_deeper_in_the_path_is_not_standard(install):
    """Only a standard prefix is packaged by default; /lib/ further down
    the path is not."""
    assert len(_check(install, "/nothing")) == 1


@pytest.mark.parametrize("install", ["/etc", "/etc/foo.conf", "/usr/bin/tool", "/lib/firmware/x"])
def test_standard_prefix_is_not_reported(install):
    assert _check(install, "/nothing") == []
