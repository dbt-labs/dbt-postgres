from contextlib import contextmanager

import psycopg2
from psycopg2.extensions import string_types

import dbt.exceptions
from dbt.adapters.base import Credentials
from dbt.adapters.sql import SQLConnectionManager
from dbt.contracts.connection import AdapterResponse
from dbt.events import AdapterLogger

from dbt.helper_types import Port
from dataclasses import dataclass
from typing import Optional
from typing_extensions import Annotated
from mashumaro.jsonschema.annotations import Maximum, Minimum
import boto3

logger = AdapterLogger("PostgresRDS")


@dataclass
class PostgresRDSCredentials(Credentials):
    host: str
    user: str
    # Annotated is used by mashumaro for jsonschema generation
    port: Annotated[Port, Minimum(0), Maximum(65535)]
    role_arn: str
    aws_region: str
    web_identity_token_path: str
    connect_timeout: int = 10
    role: Optional[str] = None
    search_path: Optional[str] = None
    keepalives_idle: int = 0  # 0 means to use the default value
    sslmode: Optional[str] = None
    sslcert: Optional[str] = None
    sslkey: Optional[str] = None
    sslrootcert: Optional[str] = None
    application_name: Optional[str] = "dbt"
    retries: int = 1

    _ALIASES = {"dbname": "database", "pass": "password"}

    @property
    def type(self):
        return "postgresrds"

    @property
    def unique_field(self):
        return self.host

    def _connection_keys(self):
        return (
            "host",
            "port",
            "user",
            "database",
            "schema",
            "connect_timeout",
            "role",
            "search_path",
            "keepalives_idle",
            "sslmode",
            "sslcert",
            "sslkey",
            "sslrootcert",
            "application_name",
            "retries",
            "role_arn",
            "web_identity_token_path",
            "aws_region",
        )


class PostgresRDSConnectionManager(SQLConnectionManager):
    TYPE = "postgresrds"

    @contextmanager
    def exception_handler(self, sql):
        try:
            yield

        except psycopg2.DatabaseError as e:
            logger.debug("Postgres error: {}".format(str(e)))

            try:
                self.rollback_if_open()
            except psycopg2.Error:
                logger.debug("Failed to release connection!")
                pass

            raise dbt.exceptions.DbtDatabaseError(str(e).strip()) from e

        except Exception as e:
            logger.debug("Error running SQL: {}", sql)
            logger.debug("Rolling back transaction.")
            self.rollback_if_open()
            if isinstance(e, dbt.exceptions.DbtRuntimeError):
                # during a sql query, an internal to dbt exception was raised.
                # this sounds a lot like a signal handler and probably has
                # useful information, so raise it without modification.
                raise

            raise dbt.exceptions.DbtRuntimeError(e) from e

    def get_web_identity_token(aws_token_path):
        with open(aws_token_path, "r") as file:
            f_data = file.readlines()
        if len(f_data) == 0:
            raise dbt.exceptions.DbtRuntimeError("No token found")
        return f_data[0]

    @classmethod
    def open(cls, connection):
        if connection.state == "open":
            logger.debug("Connection is already open, skipping open.")
            return connection

        credentials = cls.get_credentials(connection.credentials)
        kwargs = {}
        # we don't want to pass 0 along to connect() as postgres will try to
        # call an invalid setsockopt() call (contrary to the docs).
        if credentials.keepalives_idle:
            kwargs["keepalives_idle"] = credentials.keepalives_idle

        # psycopg2 doesn't support search_path officially,
        # see https://github.com/psycopg/psycopg2/issues/465
        search_path = credentials.search_path
        if search_path is not None and search_path != "":
            # see https://postgresql.org/docs/9.5/libpq-connect.html
            kwargs["options"] = "-c search_path={}".format(
                search_path.replace(" ", "\\ ")
            )

        if credentials.sslmode:
            kwargs["sslmode"] = credentials.sslmode

        if credentials.sslcert is not None:
            kwargs["sslcert"] = credentials.sslcert

        if credentials.sslkey is not None:
            kwargs["sslkey"] = credentials.sslkey

        if credentials.sslrootcert is not None:
            kwargs["sslrootcert"] = credentials.sslrootcert

        if credentials.application_name:
            kwargs["application_name"] = credentials.application_name

        def connect():
            sts_client = boto3.client("sts")

            assumed_role_object = sts_client.assume_role_with_web_identity(
                RoleArn=credentials.role_arn,
                RoleSessionName="AssumeRoleSession1",
                WebIdentityToken=cls.get_web_identity_token(
                    credentials.web_identity_token_path
                ),
            )

            aws_credentials = assumed_role_object.get("Credentials")

            boto_session = boto3.Session(
                aws_access_key_id=aws_credentials.get("AccessKeyId"),
                aws_secret_access_key=aws_credentials.get("SecretAccessKey"),
                aws_session_token=aws_credentials.get("SessionToken"),
                region_name=credentials.aws_region,
            )
            client = boto_session.client("rds")
            token = client.generate_db_auth_token(
                DBHostname=credentials.host,
                Port=credentials.port,
                DBUsername=credentials.user,
                Region=credentials.aws_region,
            )

            handle = psycopg2.connect(
                dbname=credentials.database,
                user=credentials.user,
                host=credentials.host,
                password=token,
                port=credentials.port,
                connect_timeout=credentials.connect_timeout,
                **kwargs,
            )
            if credentials.role:
                handle.cursor().execute("set role {}".format(credentials.role))
            return handle

        retryable_exceptions = [
            # OperationalError is subclassed by all psycopg2 Connection Exceptions and it's raised
            # by generic connection timeouts without an error code. This is a limitation of
            # psycopg2 which doesn't provide subclasses for errors without a SQLSTATE error code.
            # The limitation has been known for a while and there are no efforts to tackle it.
            # See: https://github.com/psycopg/psycopg2/issues/682
            psycopg2.errors.OperationalError,
        ]

        def exponential_backoff(attempt: int):
            return attempt * attempt

        return cls.retry_connection(
            connection,
            connect=connect,
            logger=logger,
            retry_limit=credentials.retries,
            retry_timeout=exponential_backoff,
            retryable_exceptions=retryable_exceptions,
        )

    def cancel(self, connection):
        connection_name = connection.name
        try:
            pid = connection.handle.get_backend_pid()
        except psycopg2.InterfaceError as exc:
            # if the connection is already closed, not much to cancel!
            if "already closed" in str(exc):
                logger.debug(f"Connection {connection_name} was already closed")
                return
            # probably bad, re-raise it
            raise

        sql = "select pg_terminate_backend({})".format(pid)

        logger.debug("Cancelling query '{}' ({})".format(connection_name, pid))

        _, cursor = self.add_query(sql)
        res = cursor.fetchone()

        logger.debug("Cancel query '{}': {}".format(connection_name, res))

    @classmethod
    def get_credentials(cls, credentials):
        return credentials

    @classmethod
    def get_response(cls, cursor) -> AdapterResponse:
        message = str(cursor.statusmessage)
        rows = cursor.rowcount
        status_message_parts = message.split() if message is not None else []
        status_messsage_strings = [
            part for part in status_message_parts if not part.isdigit()
        ]
        code = " ".join(status_messsage_strings)
        return AdapterResponse(_message=message, code=code, rows_affected=rows)

    @classmethod
    def data_type_code_to_name(cls, type_code: int) -> str:
        if type_code in string_types:
            return string_types[type_code].name
        else:
            return f"unknown type_code {type_code}"
