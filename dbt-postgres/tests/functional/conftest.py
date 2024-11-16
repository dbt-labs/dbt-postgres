import os

import pytest

from tests.functional.projects import dbt_integration


@pytest.fixture(scope="class")
def dbt_integration_project():
    return dbt_integration()


@pytest.fixture(scope="class")
def dbt_profile_target():
    return {
        "type": "postgres",
        "host": os.getenv("POSTGRES_TEST_HOST"),
        "port": int(os.getenv("POSTGRES_TEST_PORT", 0)),
        "user": os.getenv("POSTGRES_TEST_USER"),
        "pass": os.getenv("POSTGRES_TEST_PASS"),
        "dbname": os.getenv("POSTGRES_TEST_DATABASE"),
        "threads": int(os.getenv("POSTGRES_TEST_THREADS", 1)),
    }
