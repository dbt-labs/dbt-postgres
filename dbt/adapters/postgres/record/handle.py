from dbt.adapters.record import RecordReplayHandle

from dbt.adapters.postgres.record.cursor.cursor import PostgresRecordReplayCursor

class PostgresRecordReplayHandle(RecordReplayHandle):
    def cursor(self):
        cursor = None if self.native_handle is None else self.native_handle.cursor()
        return PostgresRecordReplayCursor(cursor, self.connection)
