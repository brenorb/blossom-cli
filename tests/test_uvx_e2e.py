from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
RUST_BINARY = os.environ.get("BLOSSOM_RUST_CLI_BIN") or shutil.which("blossom-cli")


@pytest.mark.e2e
def test_uvx_delegates_to_upstream_rust_cli() -> None:
    if RUST_BINARY is None:
        pytest.skip("install blossom-cli or set BLOSSOM_RUST_CLI_BIN")

    environment = os.environ.copy()
    environment["BLOSSOM_RUST_CLI_BIN"] = RUST_BINARY
    environment["BLOSSOM_CLI_NO_INSTALL"] = "1"
    result = subprocess.run(
        ["uvx", "--from", str(ROOT), "blossom-cli", "--version"],
        env=environment,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "blossom-cli" in result.stdout
