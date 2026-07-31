"""Check that the wrapper matches the published upstream blossom-cli crate."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
WRAPPER = ROOT / "src" / "blossom_cli" / "__init__.py"
CRATES_API = "https://crates.io/api/v1/crates/blossom-cli"
UPSTREAM_REPOSITORY = "https://github.com/MonumentalSystems/blossom-rs"


def read_local_versions() -> tuple[str, str]:
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")

    package_match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    rust_match = re.search(r'^RUST_VERSION\s*=\s*"([^"]+)"', wrapper, re.MULTILINE)
    if package_match is None or rust_match is None:
        raise RuntimeError("could not find both wrapper version declarations")
    return package_match.group(1), rust_match.group(1)


def read_upstream_version() -> tuple[str, str]:
    request = Request(CRATES_API, headers={"User-Agent": "blossom-cli-wrapper"})
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"could not read crates.io metadata: {exc}") from exc

    crate = payload.get("crate", {})
    repository = crate.get("repository")
    version = crate.get("max_stable_version") or crate.get("max_version")
    if repository != UPSTREAM_REPOSITORY:
        raise RuntimeError(
            "crates.io repository does not match the configured upstream: "
            f"{repository!r} != {UPSTREAM_REPOSITORY!r}"
        )
    if not version:
        raise RuntimeError("crates.io did not return a stable blossom-cli version")
    return version, repository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--offline",
        action="store_true",
        help="only compare the two local version declarations",
    )
    parser.add_argument(
        "--print-local-version",
        action="store_true",
        help="print the locally pinned Rust version after checking local consistency",
    )
    args = parser.parse_args()

    try:
        package_version, rust_version = read_local_versions()
        if package_version != rust_version:
            print(
                "Version mismatch: pyproject.toml has "
                f"{package_version}, but RUST_VERSION has {rust_version}.",
                file=sys.stderr,
            )
            return 1

        if args.print_local_version:
            print(rust_version)
            return 0

        if args.offline:
            print(f"Local wrapper versions agree: {package_version}")
            return 0

        upstream_version, repository = read_upstream_version()
        if package_version != upstream_version:
            print(
                "Upstream version mismatch: wrapper has "
                f"{package_version}, but {repository} publishes "
                f"blossom-cli {upstream_version} on crates.io.",
                file=sys.stderr,
            )
            return 1
    except (OSError, RuntimeError) as exc:
        print(f"Version check failed: {exc}", file=sys.stderr)
        return 1

    print(f"Wrapper and upstream blossom-cli agree on version {package_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
