"""Hatch build hook for wheels that contain a native upstream executable."""

import sys

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """Mark wheels as platform-specific and select a PyPI-compatible tag."""

    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        build_data["pure_python"] = False
        if sys.platform.startswith("linux"):
            build_data["tag"] = "py3-none-manylinux_2_35_x86_64"
        else:
            build_data["infer_tag"] = True
