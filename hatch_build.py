import logging
import os
import sys
from typing import Any

from hatchling.builders.config import BuilderConfig
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl

BASE_DEPS = [
    # psycopg2 dependency installed in custom hatch_build.py
    "dbt-adapters>=0.1.0a1,<2.0",
    # installed via dbt-adapters but used directly
    "dbt-common>=0.1.0a1,<2.0",
    "agate>=1.0,<2.0",
]

PSYCOPG2_MESSAGE = """
No package name override was set.
Using 'psycopg2-binary' package to satisfy 'psycopg2'

If you experience segmentation faults, silent crashes, or installation errors,
consider retrying with the 'DBT_PSYCOPG2_NAME' environment variable set to
'psycopg2'. It may require a compiler toolchain and development libraries!
""".strip()


def _dbt_psycopg2_name():
    # if the user chose something, use that
    package_name = os.getenv("DBT_PSYCOPG2_NAME", "")
    if package_name:
        return package_name

    # default to psycopg2-binary for all OSes/versions
    print(PSYCOPG2_MESSAGE)
    return "psycopg2-binary"


class CustomBuildHook(BuildHookInterface[BuilderConfig]):

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        build_data["dependencies"] = BASE_DEPS
        psycopg2_pkg_name = _dbt_psycopg2_name()
        build_data["dependencies"].append(f"{psycopg2_pkg_name}>=2.9,<3.0")


@hookimpl
def hatch_register_build_hook():
    return CustomBuildHook
