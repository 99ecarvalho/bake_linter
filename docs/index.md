# Bake Linter

Static analysis for BitBake recipes.

bake_linter checks the `.bb`, `.bbappend` and `.inc` files of Yocto Project
and OpenEmbedded layers for problems BitBake will not catch, or will only
catch late in a build:

- **licensing**: missing `LICENSE` or `LIC_FILES_CHKSUM`, typos;
- **security**: plaintext downloads, world-writable or setuid installs,
  credentials, build paths leaking into packages;
- **supply chain**: unpinned branches, unreliable hosting, bbappends that
  fetch new sources without updating the licence checksum;
- **packaging**: installed files no package contains, dependencies on
  packages the recipe never creates, `-dev` dependencies;
- **install hygiene**: `cp` that keeps the build user's ownership, missing
  modes, `/usr/local`, hardcoded host paths;
- **syntax and style**: old override syntax, quoting, ordering and
  formatting from the OpenEmbedded style guide.

It reads recipes beyond single lines (continuation lines, function bodies,
inherited classes, `require`/`include`), stays silent when it cannot know
the answer, and runs [oelint-adv](https://github.com/priv-kweihmann/oelint-adv)
as a second pass when it is installed.

## Quick start

```bash
pip install -e .                 # from a clone of the repository
bake-linter meta-mylayer/
bake-linter --output html,report.html meta-mylayer/
```

## Where to go next

- [Installation](getting-started/installation.md)
- [Quick start](getting-started/quickstart.md): options, output, exit codes
  and configuration
- [Inline suppression](INLINE_SUPPRESSION.md)
- [Rules](rules/README.md): every rule, with an example and a fix
- [Examples](examples/README.md)
