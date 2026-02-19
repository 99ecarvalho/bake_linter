#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add professional copyright notice to all Python source files in the bake_linter project.

Usage:
    python add_copyright.py [--dry-run]

Options:
    --dry-run    Show what files would be modified without actually changing them.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Copyright notice template
COPYRIGHT_NOTICE = '''# -*- coding: utf-8 -*-
"""
{module_doc}

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""
'''

# Simplified copyright header for files without module docstring
COPYRIGHT_HEADER = '''# -*- coding: utf-8 -*-
# (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
# All rights reserved.
'''

# Marker to detect already processed files
COPYRIGHT_MARKER = "(c) 2024-2026 Eduardo Correia"


def has_copyright(content: str) -> bool:
    """Check if the file already has the copyright notice."""
    return COPYRIGHT_MARKER in content


def extract_shebang(content: str) -> tuple[str, str]:
    """Extract shebang line if present."""
    lines = content.split('\n', 1)
    if lines[0].startswith('#!'):
        return lines[0] + '\n', lines[1] if len(lines) > 1 else ''
    return '', content


def extract_encoding(content: str) -> tuple[str, str]:
    """Extract encoding declaration if present."""
    lines = content.split('\n', 2)
    for i, line in enumerate(lines[:2]):
        if line.startswith('# -*- coding:') or line.startswith('# coding:'):
            # Found encoding, skip it (we'll add our own)
            rest = '\n'.join(lines[i+1:]) if i+1 < len(lines) else ''
            prefix = '\n'.join(lines[:i]) + '\n' if i > 0 else ''
            return prefix, rest
    return '', content


def extract_module_docstring(content: str) -> tuple[str, str]:
    """Extract module-level docstring if present."""
    content = content.lstrip()
    
    if content.startswith('"""'):
        # Find closing """
        end_idx = content.find('"""', 3)
        if end_idx != -1:
            docstring = content[3:end_idx].strip()
            rest = content[end_idx + 3:].lstrip()
            return docstring, rest
    elif content.startswith("'''"):
        # Find closing '''
        end_idx = content.find("'''", 3)
        if end_idx != -1:
            docstring = content[3:end_idx].strip()
            rest = content[end_idx + 3:].lstrip()
            return docstring, rest
    
    return '', content


def process_file(filepath: Path, dry_run: bool = False) -> bool:
    """
    Process a single Python file and add copyright notice.
    
    Returns True if file was modified (or would be modified in dry-run mode).
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, UnicodeDecodeError) as e:
        print(f"  ⚠️  Skipping {filepath}: {e}")
        return False
    
    # Skip if already has copyright
    if has_copyright(content):
        print(f"  ✓  {filepath} (already has copyright)")
        return False
    
    # Skip empty files
    if not content.strip():
        print(f"  ⚠️  Skipping {filepath} (empty file)")
        return False
    
    # Build new content
    new_content = ''
    
    # Extract and preserve shebang
    shebang, remaining = extract_shebang(content)
    if shebang:
        new_content += shebang
    
    # Skip existing encoding declaration (we'll add our own)
    _, remaining = extract_encoding(remaining)
    
    # Extract module docstring
    docstring, code = extract_module_docstring(remaining)
    
    if docstring:
        # Has existing docstring - merge with copyright
        # Check if docstring already mentions copyright-like content
        new_content += COPYRIGHT_NOTICE.format(module_doc=docstring)
        new_content += '\n' + code
    else:
        # No docstring - just add simple copyright header
        new_content += COPYRIGHT_HEADER
        new_content += '\n' + remaining.lstrip()
    
    if dry_run:
        print(f"  📝 Would modify: {filepath}")
        return True
    
    # Write modified content
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  ✅ Modified: {filepath}")
        return True
    except IOError as e:
        print(f"  ❌ Error writing {filepath}: {e}")
        return False


def find_python_files(root_dir: Path) -> list[Path]:
    """Find all Python files in the directory tree."""
    python_files = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip hidden directories, __pycache__, .venv, etc.
        dirnames[:] = [d for d in dirnames if not d.startswith('.') 
                       and d != '__pycache__' 
                       and d != '.venv'
                       and d != 'venv'
                       and d != '.git']
        
        for filename in filenames:
            if filename.endswith('.py'):
                python_files.append(Path(dirpath) / filename)
    
    return sorted(python_files)


def main():
    dry_run = '--dry-run' in sys.argv
    
    # Determine the root directory (bake_linter project root)
    script_dir = Path(__file__).parent.resolve()
    root_dir = script_dir
    
    print("=" * 70)
    print("  Bake Linter - Copyright Notice Tool")
    print("  (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>")
    print("=" * 70)
    print()
    
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
        print()
    
    print(f"📁 Scanning directory: {root_dir}")
    print()
    
    python_files = find_python_files(root_dir)
    
    print(f"Found {len(python_files)} Python file(s)")
    print("-" * 50)
    
    modified_count = 0
    skipped_count = 0
    
    for filepath in python_files:
        if process_file(filepath, dry_run):
            modified_count += 1
        else:
            skipped_count += 1
    
    print("-" * 50)
    print()
    print("📊 Summary:")
    if dry_run:
        print(f"   Files that would be modified: {modified_count}")
    else:
        print(f"   Files modified: {modified_count}")
    print(f"   Files skipped (already have copyright or empty): {skipped_count}")
    print()
    
    if dry_run and modified_count > 0:
        print("💡 Run without --dry-run to apply changes:")
        print(f"   python {Path(__file__).name}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
