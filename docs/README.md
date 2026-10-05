# Bake Linter Documentation Source

This directory contains the source files for the Bake Linter documentation.

## Building Documentation

The documentation is built using [MkDocs](https://www.mkdocs.org/) with the [Material theme](https://squidfunk.github.io/mkdocs-material/) inside a Docker container.

### Quick Start

```bash
# Build the HTML documentation
./build-docs.sh build

# View documentation in browser
./build-docs.sh serve
# Then open http://localhost:8001 in your browser
```

### Available Commands

| Command | Description |
|---------|-------------|
| `./build-docs.sh build` | Build static HTML documentation |
| `./build-docs.sh serve` | Start local development server on http://localhost:8001 |
| `./build-docs.sh clean` | Remove generated documentation |
| `./build-docs.sh rebuild` | Rebuild the Docker image |
| `./build-docs.sh help` | Show help message |

### Output

The generated HTML documentation is placed in `../_site/` (outside this docs folder).

This directory is ignored by git (see `.gitignore`).

## Documentation Structure

```
docs/
├── index.md                 # Main landing page
├── INLINE_SUPPRESSION.md    # Inline suppression guide
├── getting-started/         # Getting started guides
│   ├── installation.md
│   └── quickstart.md
├── examples/                # Example recipes
│   ├── README.md
│   ├── example-good.bb
│   └── example-bad.bb
├── rules/                   # Rule documentation
│   ├── README.md
│   ├── BBAPPEND001.md
│   ├── LICENSE001.md
│   └── ...
├── mkdocs.yml               # MkDocs configuration
├── Dockerfile               # Container for building docs
└── build-docs.sh            # Build script
```

## Contributing

When adding new documentation:

1. Create or edit markdown files in the appropriate directory
2. Update `mkdocs.yml` navigation if adding new pages
3. Build locally to verify: `./build-docs.sh serve`
4. Commit your changes

### Adding a New Rule

1. Create the page with `python -m bake_linter.utils.gen_docs --rule RULEID`
   and fill in the example, the reason and the fix
2. Regenerate the rule index: `python -m bake_linter.utils.gen_docs --index`
3. Add the page to the navigation in `mkdocs.yml`
4. Rebuild documentation

## Requirements

- Docker (for building documentation)
- No other dependencies required - everything runs in the container

## Troubleshooting

### Permission Issues

If you encounter permission issues with the `_site` directory, run:
```bash
./build-docs.sh clean
```

### Docker Image Rebuild

If you modify the Dockerfile, rebuild the image:
```bash
./build-docs.sh rebuild
```
