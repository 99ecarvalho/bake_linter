#!/usr/bin/env bash
# Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
# SPDX-License-Identifier: LGPL-3.0-or-later
#
# Installs bake-linter globally via pipx, in editable mode, and injects
# oelint-adv (vendored as a git submodule) into the same environment.
#
# After running this script, the `bake-linter` command is available in
# any directory, with no need to manually activate a venv. Since the
# install is --editable, changes to this repo's code are picked up
# automatically by the installed command (no reinstall needed).
#
# Usage:
#   ./install.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Checking for pipx..."
if ! command -v pipx >/dev/null 2>&1; then
    echo "pipx not found on this system."
    if command -v apt-get >/dev/null 2>&1; then
        echo "Installing pipx via apt (this will prompt for your sudo password)..."
        sudo apt-get update -qq
        sudo apt-get install -y pipx
    else
        echo "Please install pipx manually and re-run this script." >&2
        echo "e.g.: python3 -m pip install --user pipx" >&2
        exit 1
    fi
fi

# Make sure ~/.local/bin is on PATH for pipx-installed binaries.
pipx ensurepath >/dev/null 2>&1 || true

echo "==> Ensuring the oelint-adv submodule is initialized..."
git -C "$SCRIPT_DIR" submodule update --init --recursive

echo "==> Installing bake-linter via pipx (editable mode)..."
pipx install --editable "$SCRIPT_DIR" --force

echo "==> Injecting oelint-adv into the bake-linter environment..."
pipx inject bake-linter --editable "$SCRIPT_DIR/vendor/oelint-adv" --force

echo
echo "Installation complete."
echo "If 'bake-linter' is not found yet, open a new terminal (or run 'source ~/.bashrc')."
echo "Test with: bake-linter --version"
