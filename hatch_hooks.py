import os
import subprocess
import sys

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl


class Psycopg2NoBinary(BuildHookInterface):
    """
    Custom build hook to install psycopg2 instead of psycopg2-binary based on the presence of `DBT_PSYCOPG2_NAME`.
    This is necessary as psycopg2-binary is better for local development, but psycopg2 is better for production.
    """

    PLUGIN_NAME = "psycopg2"

    def finalize(self, version, build_data, artifact_path) -> None:
        if os.getenv("DBT_PSYCOPG2_NAME", "") == "psycopg2":
            psycopg2_binary_pinned = [
                package
                for package in build_data["dependencies"]
                if package.startswith("psycopg2-binary")
            ].pop()
            psycopg2_pinned = psycopg2_binary_pinned.replace("-binary", "")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "-y", "uninstall", "psycopg2-binary"]
            )
            subprocess.check_call(
                [sys.executable, "-m", "pip", "-y", "install", f'"{psycopg2_pinned}"']
            )


@hookimpl
def hatch_register_build_hook():
    return Psycopg2NoBinary
