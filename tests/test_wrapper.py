from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[1] / "src" / "blossom_cli" / "__init__.py"
SPEC = importlib.util.spec_from_file_location("blossom_cli_wrapper", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
wrapper = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = wrapper
SPEC.loader.exec_module(wrapper)


def test_cache_root_honors_explicit_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    monkeypatch.setenv("BLOSSOM_CLI_CACHE_DIR", str(cache))

    assert wrapper.cache_root() == cache


def test_resolve_binary_uses_explicit_upstream_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    binary = tmp_path / "blossom-cli"
    binary.write_text("#!/bin/sh\n")
    binary.chmod(0o700)
    monkeypatch.setenv("BLOSSOM_RUST_CLI_BIN", str(binary))

    assert wrapper.resolve_binary() == binary


def test_path_binary_does_not_return_the_wrapper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wrapper.shutil, "which", lambda _: sys.argv[0])

    assert wrapper.path_binary() is None


def test_bundled_binary_uses_platform_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    package = tmp_path / "blossom_cli"
    binary = package / "bin" / "linux-x86_64" / "blossom-cli"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/sh\n")
    binary.chmod(0o700)

    monkeypatch.setattr(wrapper, "__file__", str(package / "__init__.py"))
    monkeypatch.setattr(wrapper, "bundled_platform", lambda: "linux-x86_64")

    assert wrapper.bundled_binary() == binary


def test_resolve_binary_prefers_bundled_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bundled = tmp_path / "bundled-blossom-cli"
    bundled.write_text("#!/bin/sh\n")
    bundled.chmod(0o700)
    on_path = tmp_path / "path-blossom-cli"
    on_path.write_text("#!/bin/sh\n")
    on_path.chmod(0o700)

    monkeypatch.delenv("BLOSSOM_RUST_CLI_BIN", raising=False)
    monkeypatch.setattr(wrapper, "bundled_binary", lambda: bundled)
    monkeypatch.setattr(wrapper, "path_binary", lambda: on_path)

    assert wrapper.resolve_binary() == bundled


def test_install_is_blocked_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BLOSSOM_CLI_NO_INSTALL", "1")

    with pytest.raises(wrapper.WrapperError, match="automatic installation is disabled"):
        wrapper.install_binary()
