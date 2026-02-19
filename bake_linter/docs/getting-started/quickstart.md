# Quick Start

This guide will help you get started with Bake Linter in just a few minutes.

## Basic Usage

### Lint a Directory

```bash
# Lint current directory
bake-linter .

# Lint a specific layer
bake-linter meta-layer/

# Lint specific recipe files
bake-linter recipes-core/base-files/base-files_%.bb
```

### Lint with Output Files

```bash
# Generate JSON output
bake-linter --output json,results.json .

# Generate HTML report
bake-linter --output html,report.html .

# Generate multiple formats
bake-linter --output json,results.json --output html,report.html .
```

## Understanding Output

### Console Output

```
recipes-core/myapp/myapp_1.0.bb:5: error: LICENSE001 - Missing LICENSE variable
recipes-core/myapp/myapp_1.0.bb:12: warning: STYLE002 - Line exceeds 100 characters
```

Format: `FILE:LINE: SEVERITY: RULE_ID - MESSAGE`

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - no issues found |
| 1 | Errors found |
| 2 | Warnings found (no errors) |
| 3 | Runtime/configuration error |

## Common Options

### Filtering Rules

```bash
# Enable specific rules only
bake-linter --enable LICENSE001,MANDATORY001 .

# Disable specific rules
bake-linter --disable STYLE001,STYLE002 .

# List all available rules
bake-linter --list-rules
```

### Excluding Files

```bash
# Exclude directories
bake-linter --exclude 'build/*' --exclude 'tmp/*' .

# Exclude specific files
bake-linter --exclude '*.bak' --exclude 'test_*' meta-layer/
```

### CI Mode

```bash
# No colors, strict exit codes
bake-linter --ci .

# Treat warnings as errors
bake-linter --warnings-as-errors .
```

## Configuration File

Create `.bake-linter.yaml` in your project root:

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

## Inline Suppression

Suppress rules directly in your recipes:

```bitbake
# Suppress for next line
# nolint: LICENSE001
LICENSE = "CLOSED"

# Suppress inline
RDEPENDS:${PN} = "bash"  # nolint: DEPENDENCY001
```

See [Inline Suppression](../INLINE_SUPPRESSION.md) for more details.

## Next Steps

- [Rules Reference](../rules/README.md) - Explore all available rules
- [Examples](../examples/README.md) - See example recipes
- [Inline Suppression](../INLINE_SUPPRESSION.md) - Learn suppression syntax
