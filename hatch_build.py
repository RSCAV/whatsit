"""The wheel carries a compiled arm64 binary, so it must not be tagged py3-none-any."""
import platform
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class PlatformWheel(BuildHookInterface):
    PLUGIN_NAME = "platform-wheel"

    def initialize(self, version, build_data):
        if platform.system() != "Darwin":
            return
        arch = "arm64" if platform.machine() == "arm64" else "x86_64"
        build_data["tag"] = f"py3-none-macosx_13_0_{arch}"
        build_data["pure_python"] = False
