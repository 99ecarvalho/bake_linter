# Installation

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation Methods

### From Source (Development)

```bash
# Navigate to the linter directory
cd tools/bake_linter

# (Optional) Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install from source
pip install -e .

# Or with development dependencies (for testing/development)
pip install -e ".[dev]"
```

The `egg-info` directory will be created automatically by setuptools during installation—this is normal and expected.

### Using Requirements File

```bash
cd tools/bake_linter
pip install -r requirements.txt
pip install -e .
```

## Verifying Installation

After installation, verify that the linter is available:

```bash
bake-linter --version
bake-linter --help
```

## Updating

To update to the latest version:

```bash
cd tools/bake_linter
git pull
pip install -e .
```

## Uninstalling

```bash
pip uninstall bake-linter
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Learn basic usage
- [Rules Reference](../rules/README.md) - Explore available rules
- [Configuration](../index.md#configuration) - Customize the linter
