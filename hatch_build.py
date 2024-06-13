import os

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl


class Psycopg2BuildHook(BuildHookInterface):
    """
    Replace `psycopg2-binary` with the same version of `psycopg2`
    when configured via `DBT_PSYCOPG2_NAME=psycopg2`
    """

    def initialize(self, version, build_data):
        if os.getenv("DBT_PSYCOPG2_NAME") == "psycopg2":
            psycopg2_binary = [
                dep
                for dep in self.metadata._core.config.get("dependencies")
                if dep.startswith("psycopg2-binary")
            ].pop()
            if psycopg2_binary:
                psycopg2_no_binary = psycopg2_binary.replace("-binary", "")
                self.metadata._core.config["dependencies"].remove(psycopg2_binary)
                self.metadata._core.config["dependencies"].append(psycopg2_no_binary)
            else:
                raise ImportError("`psycopg2-binary not found")


@hookimpl
def hatch_register_build_hook():
    return Psycopg2BuildHook
