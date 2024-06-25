from dbt.tests.adapter.dbt_show.test_dbt_show import (
    BaseShowSqlHeader,
    BaseShowLimit,
    BaseShowDoesNotHandleDoubleLimit,
)


class TestPostgresShowSqlHeader(BaseShowSqlHeader):
    pass


class TestPostgresShowLimit(BaseShowLimit):
    pass


class TestPostgresShowDoesNotHandleDoubleLimit(BaseShowDoesNotHandleDoubleLimit):
    pass
