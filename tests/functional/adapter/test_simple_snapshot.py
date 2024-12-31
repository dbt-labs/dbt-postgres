from dbt.tests.adapter.simple_snapshot.test_snapshot import (
    BaseSimpleSnapshot,
    BaseSnapshotCheck,
)
from dbt.tests.adapter.simple_snapshot.new_record_mode import (
    SnapshotNewRecordMode,
)


class TestSnapshot(BaseSimpleSnapshot):
    pass


class TestSnapshotCheck(BaseSnapshotCheck):
    pass


class TestPostgresSnapshotNewRecordMode(SnapshotNewRecordMode):
    pass
