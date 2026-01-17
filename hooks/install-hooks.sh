#!/usr/bin/env bash
#
# Install Bake Linter git hooks
#

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)
HOOKS_DIR="${REPO_ROOT}/.git/hooks"

echo "Installing Bake Linter git hooks..."
echo ""

# Install pre-commit hook
if [ -f "${HOOKS_DIR}/pre-commit" ] && [ ! -L "${HOOKS_DIR}/pre-commit" ]; then
    echo "⚠ Existing pre-commit hook found. Backing up to pre-commit.backup"
    mv "${HOOKS_DIR}/pre-commit" "${HOOKS_DIR}/pre-commit.backup"
fi

ln -sf "../../tools/bake_linter/hooks/pre-commit" "${HOOKS_DIR}/pre-commit"
chmod +x "${SCRIPT_DIR}/pre-commit"

echo "✓ pre-commit hook installed"
echo ""
echo "The hook will automatically lint staged .bb, .bbappend, and .inc files."
echo "To bypass: git commit --no-verify"
echo ""
echo "To uninstall: rm ${HOOKS_DIR}/pre-commit"
