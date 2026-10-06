"""
Include runtime documentation and defaults in built distributions.

Copyright (c) 2026 OpenAI

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithResources(build_py):
    def run(self):
        super().run()
        root = Path(__file__).parent
        target = Path(self.build_lib) / 'bake_linter' / 'data'
        self.copy_tree(str(root / 'docs' / 'rules'), str(target / 'rules'))
        self.mkpath(str(target / 'config'))
        self.copy_file(str(root / 'config' / '.bake-linter.yaml'),
                       str(target / 'config' / '.bake-linter.yaml'))


setup(cmdclass={'build_py': BuildWithResources})
