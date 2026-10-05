#!/usr/bin/env bash
# Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
# SPDX-License-Identifier: LGPL-3.0-or-later
#
# Install the Bake Linter pre-commit hook into a git repository.
#
# Usage: install-hooks.sh [REPO]
#   REPO defaults to the repository containing the current directory.
#

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TARGET=${1:-.}
REPO_ROOT=$(git -C "$TARGET" rev-parse --show-toplevel)
HOOKS_DIR=$(cd "$REPO_ROOT" && mkdir -p "$(git rev-parse --git-path hooks)" && cd "$(git rev-parse --git-path hooks)" && pwd)

echo "Installing Bake Linter git hooks into ${REPO_ROOT}..."
echo ""

# Install pre-commit hook
if [ -f "${HOOKS_DIR}/pre-commit" ] && [ ! -L "${HOOKS_DIR}/pre-commit" ]; then
    echo "⚠ Existing pre-commit hook found. Backing up to pre-commit.backup"
    mv "${HOOKS_DIR}/pre-commit" "${HOOKS_DIR}/pre-commit.backup"
fi

ln -sf "${SCRIPT_DIR}/pre-commit" "${HOOKS_DIR}/pre-commit"
chmod +x "${SCRIPT_DIR}/pre-commit"

echo "✓ pre-commit hook installed"
echo ""
echo "The hook will automatically lint staged .bb, .bbappend, and .inc files."
echo "To bypass: git commit --no-verify"
echo ""
echo "To uninstall: rm ${HOOKS_DIR}/pre-commit"
