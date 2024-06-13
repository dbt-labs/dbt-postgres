from importlib.metadata import version as get_version
import os
import subprocess
from typing import Any, Dict

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl


class Psycopg2BuildHook(BuildHookInterface):
    """
    Replace `psycopg2-binary` with the same version of `psycopg2`
    when configured via `DBT_PSYCOPG2_NAME=psycopg2`
    """

    def finalize(self, version: str, build_data: Dict[str, Any], artifact_path: str) -> None:
        if os.getenv("DBT_PSYCOPG2_NAME") == "psycopg2":
            psycopg2_version = get_version("psycopg2-binary")
            subprocess.run("pip", "uninstall", "-y", "psycopg2-binary")
            subprocess.run("pip", "install", f"psycopg2=={psycopg2_version}")


@hookimpl
def hatch_register_build_hook():
    return Psycopg2BuildHook
