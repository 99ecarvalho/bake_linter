# Installation

## Requirements

- Python 3.9 or newer for bake_linter.
- Python 3.10 or newer for oelint-adv, which is optional.
- git, to clone the repository and its oelint-adv submodule.

## From a clone

```bash
git clone --recurse-submodules https://github.com/99ecarvalho/bake_linter.git
cd bake_linter

python3 -m venv .venv
source .venv/bin/activate

pip install -e .                     # bake_linter
pip install -e ./vendor/oelint-adv   # optional: oelint-adv
```

For development, install the test dependencies too:

```bash
pip install -e ".[dev]"
```

If you cloned without `--recurse-submodules`, fetch oelint-adv with
`git submodule update --init`.

## For your user, with pipx

```bash
./install.sh
```

The script:

1. installs [pipx](https://pipx.pypa.io/) if it is missing. On Debian and
   Ubuntu it runs `sudo apt-get install pipx`, so it may ask for your
   password; elsewhere it tells you how to install pipx;
2. initialises the oelint-adv submodule;
3. installs bake_linter and oelint-adv in editable mode, so the
   `bake-linter` command follows the checkout after a `git pull`.

Open a new terminal if `bake-linter` is not found yet.

## From Git, without a clone

```bash
pip install git+https://github.com/99ecarvalho/bake_linter.git
pip install oelint-adv               # optional
```

## Check the installation

```bash
bake-linter --version
bake-linter --list-rules
```

To see whether oelint-adv is found, and why not, run any lint with
`--debug`.

## Updating

```bash
git pull
git submodule update --init
```

An editable install picks up the new code; reinstall only after changes to
`pyproject.toml`.
