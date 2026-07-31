"""Hatch build hook for wheels that contain a native upstream executable."""

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """Mark wheels as platform-specific and infer the runner's wheel tag."""

    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        build_data["pure_python"] = False
        build_data["infer_tag"] = True
