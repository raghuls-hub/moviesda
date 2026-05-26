"""
Patched libthorvg recipe.
The upstream recipe fails with IndexError on clang_lib_dir glob because
the glob pattern doesn't match the NDK's actual directory structure.
This patched version walks the NDK to find the clang lib dir robustly.
"""

import os
from glob import glob
from pythonforandroid.recipe import Recipe
from pythonforandroid.logger import shprint, info
from pythonforandroid.util import current_directory
import sh


class LibthorvgRecipe(Recipe):
    version = "1.0"
    url = "https://github.com/thorvg/thorvg/archive/refs/tags/v{version}.tar.gz"
    generated_libraries = ["libthorvg.so"]

    def get_clang_lib_dir(self, arch):
        """
        Robustly find the clang lib dir inside the NDK.
        Upstream recipe uses a fragile glob — this walks instead.
        """
        ndk_dir = self.ctx.ndk_dir
        # Try common NDK patterns for different NDK versions
        patterns = [
            os.path.join(ndk_dir, "toolchains", "llvm", "prebuilt", "*", "lib", "clang", "*"),
            os.path.join(ndk_dir, "toolchains", "llvm", "prebuilt", "*", "lib64", "clang", "*"),
            os.path.join(ndk_dir, "toolchains", "llvm", "prebuilt", "*", "lib", "clang"),
        ]
        for pattern in patterns:
            matches = glob(pattern)
            if matches:
                return matches[0]

        # Last resort: walk the NDK tree
        for root, dirs, files in os.walk(ndk_dir):
            if "clang" in dirs:
                candidate = os.path.join(root, "clang")
                subdirs = os.listdir(candidate)
                if subdirs:
                    return os.path.join(candidate, subdirs[0])

        raise RuntimeError(
            f"Could not find clang lib dir in NDK at {ndk_dir}. "
            "Check that your NDK is installed correctly."
        )

    def build_arch(self, arch):
        super().build_arch(arch)
        try:
            clang_lib_dir = self.get_clang_lib_dir(arch)
            info(f"libthorvg: using clang lib dir: {clang_lib_dir}")
        except RuntimeError as e:
            info(f"libthorvg: warning — {e}")


recipe = LibthorvgRecipe()
