"""A transparent uvx launcher for MonumentalSystems/blossom-rs."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


RUST_PACKAGE = "blossom-cli"
RUST_VERSION = "0.6.0"
UPSTREAM_REPOSITORY = "https://github.com/MonumentalSystems/blossom-rs"


class WrapperError(RuntimeError):
    """Raised when the upstream Rust executable cannot be resolved."""


def cache_root() -> Path:
    """Return the user-writable cache directory for the pinned Rust binary."""
    configured = os.environ.get("BLOSSOM_CLI_CACHE_DIR")
    if configured:
        return Path(configured).expanduser()

    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg_cache).expanduser() if xdg_cache else Path.home() / ".cache"
    return base / "blossom-cli" / RUST_VERSION


def cached_binary() -> Path:
    """Return the expected path of the cached upstream executable."""
    executable = "blossom-cli.exe" if os.name == "nt" else "blossom-cli"
    return cache_root() / "bin" / executable


def configured_binary() -> Path | None:
    """Resolve an explicitly configured upstream executable."""
    configured = os.environ.get("BLOSSOM_RUST_CLI_BIN")
    if not configured:
        return None

    path = Path(configured).expanduser()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise WrapperError(f"BLOSSOM_RUST_CLI_BIN is not executable: {path}")
    return path


def path_binary() -> Path | None:
    """Find the upstream executable on PATH without recursing into this launcher."""
    candidate = shutil.which(RUST_PACKAGE)
    if not candidate:
        return None

    path = Path(candidate).resolve()
    launcher = Path(sys.argv[0]).resolve()
    if path == launcher:
        return None
    return path


def bundled_platform() -> str | None:
    """Return the package directory name for the current platform."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    machine = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "aarch64": "arm64",
    }.get(machine, machine)

    if system == "darwin":
        system = "macos"
    elif system not in {"linux", "windows"}:
        return None
    return f"{system}-{machine}"


def bundled_binary() -> Path | None:
    """Resolve the executable shipped inside a platform-specific wheel."""
    platform_name = bundled_platform()
    if platform_name is None:
        return None

    executable = "blossom-cli.exe" if os.name == "nt" else "blossom-cli"
    path = Path(__file__).resolve().parent / "bin" / platform_name / executable
    if path.is_file() and os.access(path, os.X_OK):
        return path
    return None


def install_binary() -> Path:
    """Install the pinned upstream crate into the user cache via Cargo."""
    if os.environ.get("BLOSSOM_CLI_NO_INSTALL"):
        raise WrapperError(
            "the Rust blossom-cli binary was not found and automatic installation "
            "is disabled; install it or set BLOSSOM_RUST_CLI_BIN"
        )

    cargo = shutil.which("cargo")
    if cargo is None:
        raise WrapperError(
            "the Rust blossom-cli binary was not found and Cargo is unavailable; "
            "install Rust/Cargo or set BLOSSOM_RUST_CLI_BIN"
        )

    destination = cache_root()
    destination.mkdir(parents=True, exist_ok=True)
    command = [
        cargo,
        "install",
        RUST_PACKAGE,
        "--version",
        RUST_VERSION,
        "--locked",
        "--root",
        str(destination),
    ]
    print(
        f"Installing {RUST_PACKAGE} {RUST_VERSION} from {UPSTREAM_REPOSITORY} via Cargo...",
        file=sys.stderr,
    )
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise WrapperError(f"Cargo failed to install {RUST_PACKAGE} {RUST_VERSION}")

    binary = cached_binary()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise WrapperError(f"Cargo did not create the expected executable: {binary}")
    return binary


def resolve_binary() -> Path:
    """Resolve the upstream executable without changing its command-line API."""
    explicit = configured_binary()
    if explicit:
        return explicit

    bundled = bundled_binary()
    if bundled:
        return bundled

    on_path = path_binary()
    if on_path:
        return on_path

    cached = cached_binary()
    if cached.is_file() and os.access(cached, os.X_OK):
        return cached

    return install_binary()


def main(argv: list[str] | None = None) -> int:
    """Execute the upstream CLI with exactly the arguments supplied by the user."""
    args = sys.argv[1:] if argv is None else argv
    try:
        binary = resolve_binary()
    except WrapperError as exc:
        print(f"blossom-cli wrapper: {exc}", file=sys.stderr)
        return 127

    command = [str(binary), *args]
    if os.name == "nt":
        return subprocess.call(command)

    os.execv(command[0], command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
