# Contributor and agent instructions

## Upstream is the source of truth

This repository is a thin Python wrapper around the Rust `blossom-cli` crate.
The upstream project is [`MonumentalSystems/blossom-rs`](https://github.com/MonumentalSystems/blossom-rs).

The wrapper must use the latest stable `blossom-cli` version published on
crates.io. The GitHub repository can contain unreleased work, so do not pin the
wrapper to a version that is only present on the upstream `main` branch. The
build pipeline installs the published crate with `cargo install`, which makes
crates.io the distribution source of truth.

Published platform wheels contain the compiled upstream executable. Supported
platforms are Linux x86_64, macOS x86_64, macOS arm64, and Windows x86_64. The
source distribution remains a fallback for unsupported platforms.

These values must always match the published upstream crate version:

- `project.version` in `pyproject.toml`;
- `RUST_VERSION` in `src/blossom_cli/__init__.py`;
- the Git tag and GitHub release used to publish the wrapper to PyPI.

Run the version check before changing any of these values:

```bash
uv run python scripts/check_upstream_version.py
```

When working offline, the local consistency check is still available:

```bash
uv run python scripts/check_upstream_version.py --offline
```

## Required checks

Before committing changes, run:

```bash
uvx pre-commit run --all-files
uv run pytest
uv build
```

Do not change the upstream Rust CLI's command-line API. Changes in this
repository should only affect packaging, resolution, documentation, or the
transparent process wrapper.

## Release workflow

When a new upstream version is published:

1. Run the online version check.
2. Update `pyproject.toml` and `RUST_VERSION` together.
3. Regenerate `uv.lock` with `uv lock`.
4. Update release documentation or examples that contain the version.
5. Run all required checks.
6. Create the wrapper tag and GitHub release with the same version as the Rust
   crate.

The version CI and pre-commit hook are intentionally part of this repository's
release guardrails. Keep them working when changing the packaging layout.

The publish workflow builds the upstream binary separately on each supported
runner, places it under `src/blossom_cli/bin/<platform>/`, and uploads the
platform-specific wheels to PyPI. Do not commit compiled binaries to Git.
