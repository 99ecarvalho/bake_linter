#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Documentation generator for bake-linter rules.

This script generates markdown documentation for all rules based on their
class definitions and a template.

Usage:
    python -m bake_linter.utils.gen_docs [--force]

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from bake_linter.core.registry import get_registry


def get_template() -> str:
    """Load the documentation template."""
    template_path = Path(__file__).parent.parent.parent / "docs" / "rules" / "template.md"
    
    if not template_path.exists():
        print(f"Error: Template not found at {template_path}", file=sys.stderr)
        sys.exit(1)
    
    return template_path.read_text()


def generate_doc_for_rule(rule_cls, template: str, force: bool = False) -> Optional[Path]:
    """
    Generate documentation for a single rule.
    
    Args:
        rule_cls: The rule class
        template: The template string
        force: Whether to overwrite existing documentation
        
    Returns:
        Path to the generated file, or None if skipped
    """
    docs_dir = Path(__file__).parent.parent.parent / "docs" / "rules"
    output_file = docs_dir / f"{rule_cls.rule_id}.md"
    
    # Skip if exists and not forcing
    if output_file.exists() and not force:
        print(f"Skipping {rule_cls.rule_id} (already exists, use --force to overwrite)")
        return None
    
    # Extract rule information
    rule_id = rule_cls.rule_id
    name = rule_cls.name
    description = rule_cls.description
    severity = str(rule_cls.default_severity)
    enabled = "Yes" if rule_cls.enabled_by_default else "No"
    
    # Determine category from groups
    category = rule_cls.groups[0] if rule_cls.groups else "general"
    
    # Basic placeholders - in a full implementation, you'd extract these from
    # docstrings or additional metadata
    content = template
    content = content.replace("{RULE_ID}", rule_id)
    content = content.replace("{RULE_NAME}", name)
    content = content.replace("{SEVERITY}", severity)
    content = content.replace("{CATEGORY}", category)
    content = content.replace("{ENABLED}", enabled)
    content = content.replace("{DESCRIPTION}", description)
    
    # Placeholders that need manual filling
    content = content.replace("{BAD_EXAMPLE}", "# TODO: Add example of code that violates this rule")
    content = content.replace("{WHY_BAD}", "TODO: Explain why this pattern is problematic")
    content = content.replace("{GOOD_EXAMPLE}", "# TODO: Add example of correct code")
    content = content.replace("{FIX_EXPLANATION}", "TODO: Explain how to fix the issue")
    content = content.replace("{OPTIONS_EXAMPLE}", "# options:\n    #   key: value  # TODO: Add rule-specific options if any")
    
    # Write the file
    output_file.write_text(content)
    print(f"Generated documentation for {rule_id} -> {output_file}")
    
    return output_file


def main():
    """Main entry point for documentation generator."""
    parser = argparse.ArgumentParser(
        description="Generate documentation for bake-linter rules"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing documentation files"
    )
    parser.add_argument(
        "--rule",
        metavar="RULE_ID",
        help="Generate documentation for a specific rule only"
    )
    
    args = parser.parse_args()
    
    # Load template
    template = get_template()
    
    # Discover all rules
    registry = get_registry()
    registry.discover_rules()
    
    # Get rules to document
    if args.rule:
        rules = {args.rule: registry.get_all_rules().get(args.rule)}
        if rules[args.rule] is None:
            print(f"Error: Rule {args.rule} not found", file=sys.stderr)
            sys.exit(1)
    else:
        rules = registry.get_all_rules()
    
    # Generate documentation
    generated = []
    skipped = []
    
    for rule_id, rule_cls in sorted(rules.items()):
        result = generate_doc_for_rule(rule_cls, template, args.force)
        if result:
            generated.append(rule_id)
        else:
            skipped.append(rule_id)
    
    # Summary
    print("\n" + "=" * 70)
    print(f"Documentation generation complete!")
    print(f"  Generated: {len(generated)} files")
    print(f"  Skipped: {len(skipped)} files")
    
    if generated:
        print(f"\nGenerated files need manual editing to fill in:")
        print("  - Bad code examples")
        print("  - Why it's bad explanations")
        print("  - Good code examples")
        print("  - Fix explanations")
        print("  - Configuration options (if applicable)")
    
    print("\nNext steps:")
    print("  1. Review generated files in docs/rules/")
    print("  2. Fill in TODO placeholders with actual examples")
    print("  3. Test the documentation with real users")
    print("=" * 70)


if __name__ == "__main__":
    main()
