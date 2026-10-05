# Bake Linter Documentation

Static analysis for BitBake recipes.

## Overview

Bake Linter helps you maintain high-quality BitBake recipes by checking for:

- **License compliance** - Ensure proper licensing declarations
- **Security issues** - Detect potential security vulnerabilities
- **Style consistency** - Enforce coding standards
- **Best practices** - Follow Yocto/OE community guidelines
- **Deprecated syntax** - Identify outdated patterns

## Features

- **Modular Rule System**: Each lint rule is self-contained and auto-discovered
- **Extensible**: Add new rules with minimal code and no refactoring
- **CI-Friendly**: Supports multiple output formats, strict exit codes, and no-color mode
- **Configurable**: YAML/JSON configuration files with CLI overrides
- **Multiple Output Formats**: Text (colored), JSON, JSON Lines, HTML reports
- **Yocto-Specific**: Built-in rules for license checks, deprecated syntax, naming conventions, and security

## Quick Start

```bash
# Lint current directory
bake-linter .

# Lint specific files or directories
bake-linter meta-layer/recipes-core/

# Generate HTML report
bake-linter --output html,report.html .

# CI mode (no colors, strict exit codes)
bake-linter --ci .

# List all available rules
bake-linter --list-rules
```

## Documentation Sections

- **[Getting Started](getting-started/installation.md)** - Installation and setup
- **[Inline Suppression](INLINE_SUPPRESSION.md)** - How to suppress rules inline
- **[Examples](examples/README.md)** - Example recipes and usage patterns
- **[Rules Reference](rules/README.md)** - Complete rule documentation

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - no issues found |
| 1 | Errors found |
| 2 | Warnings found (no errors) |
| 3 | Runtime/configuration error |

## Configuration

Create a `.bake-linter.yaml` file in your project root:

```yaml
rules:
  LICENSE001:
    enabled: true
    severity: error

  STYLE001:
    enabled: false

settings:
  exclude:
    - "build/*"
    - "tmp/*"
```

## Rule Categories

| Category | Description |
|----------|-------------|
| BBAPPEND | Rules for .bbappend files |
| BESTPRACTICE | General best practices |
| COMPAT | Compatibility checks |
| DEPENDENCY | Dependency management |
| DEPRECATED | Deprecated syntax detection |
| DOC | Documentation checks |
| FUNCTION | Function usage rules |
| INSTALL | Installation rules |
| LAYER | Layer configuration |
| LICENSE | License compliance |
| LIFECYCLE | Recipe lifecycle |
| MANDATORY | Required variables |
| METADATA | Metadata checks |
| NAMING | Naming conventions |
| PATCH | Patch handling |
| PKG | Package rules |
| PORT | Portability checks |
| PYTHON | Python-specific rules |
| REPRO | Reproducibility |
| SECURITY | Security checks |
| SRCREV | Source revision rules |
| STYLE | Code style |
| SUPPLY | Supply chain security |
| SYNTAX | Syntax validation |
| SYSTEMD | Systemd integration |
| TASK | Task definitions |
| URI | URI validation |
| VARIABLES | Variable usage |

---

*Bake Linter - Keeping your BitBake recipes clean and secure*
