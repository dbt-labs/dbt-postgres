import dataclasses
from typing import Optional

from dbt.adapters.record import RecordReplayHandle, RecordReplayCursor
from dbt_common.record import record_function, Record, Recorder


class PostgresRecordReplayHandle(RecordReplayHandle):
    # PAW: Wrap
    def cursor(self):
        cursor = None if self.native_handle is None else self.native_handle.cursor()
        return PostgresRecordReplayCursor(cursor, self.connection)


@dataclasses.dataclass
class CursorGetStatusMessageParams:
    connection_name: str


@dataclasses.dataclass
class CursorGetStatusMessageResult:
    msg: Optional[str]


class CursorGetStatusMessageRecord(Record):
    params_cls = CursorGetStatusMessageParams
    result_cls = CursorGetStatusMessageResult


Recorder.register_record_type(CursorGetStatusMessageRecord)


class PostgresRecordReplayCursor(RecordReplayCursor):
    @property
    @record_function(CursorGetStatusMessageRecord, method=True, id_field_name="connection_name")
    def statusmessage(self):
        return self.native_cursor.statusmessage
