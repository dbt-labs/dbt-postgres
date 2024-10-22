from dbt.tests.adapter.incremental.test_incremental_microbatch import (
    BaseTestMicrobatchOn,
    BaseTestMicrobatchOff,
)


class TestPostgresMicrobatchOn(BaseTestMicrobatchOn):
    pass


class TestPostgresMicrobatchOff(BaseTestMicrobatchOff):
    pass
