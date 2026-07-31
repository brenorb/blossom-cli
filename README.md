# blossom-cli

`blossom-cli` is a thin Python wrapper that makes the upstream Rust Blossom client available through `uvx`:

```bash
uvx blossom-cli --version
uvx blossom-cli status
uvx blossom-cli upload ./file.pdf
```

The wrapper preserves the upstream command-line API. It does not add, rename, or reinterpret Rust CLI commands. Platform-specific PyPI wheels contain the compiled Rust executable, so supported platforms do not need Rust or Cargo installed. It resolves the upstream executable in this order:

1. `BLOSSOM_RUST_CLI_BIN`, when explicitly configured.
2. The executable bundled in the platform wheel.
3. A `blossom-cli` executable already available on `PATH`.
4. A versioned executable in the user cache.
5. `cargo install blossom-cli --version 0.5.6 --locked` into the user cache as a fallback for source distributions and unsupported platforms.

The published wheels currently target Linux x86_64, macOS x86_64, macOS arm64, and Windows x86_64. On those platforms, a normal invocation is enough:

```bash
uvx blossom-cli --version
```

This package does not contain or reimplement the Blossom protocol. The Rust executable and protocol implementation come from [`MonumentalSystems/blossom-rs`](https://github.com/MonumentalSystems/blossom-rs), which is published under the MIT License. This project exists only to provide a convenient `uvx` entry point for that upstream project.

## Configuration

The upstream CLI continues to own all options and environment variables, including `BLOSSOM_SECRET_KEY`:

```bash
export BLOSSOM_SERVER="https://blossom.example.com"
export BLOSSOM_SECRET_KEY="<your-secret-key>"

uvx blossom-cli --server "$BLOSSOM_SERVER" --format json --no-publish upload ./file.pdf
```

Use `uvx blossom-cli --help` for the complete command surface. Read the upstream documentation for Blossom protocol behavior and server compatibility.

## Development

```bash
uv sync --dev
uv run pytest
uv build
```

To test the wrapper against a locally available Rust executable without compiling anything:

```bash
BLOSSOM_RUST_CLI_BIN=/path/to/blossom-cli uvx --from . blossom-cli --version
```

## License

The wrapper code is released under the MIT License; see [LICENSE](LICENSE). The upstream project has separate MIT license terms reproduced in [licenses/blossom-rs-MIT.txt](licenses/blossom-rs-MIT.txt).
