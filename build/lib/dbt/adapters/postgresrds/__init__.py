# these are mostly just exports, #noqa them so flake8 will be happy
from dbt.adapters.postgresrds.connections import PostgresRDSConnectionManager  # noqa
from dbt.adapters.postgresrds.connections import PostgresRDSCredentials
from dbt.adapters.postgresrds.column import PostgresRDSColumn  # noqa
from dbt.adapters.postgresrds.relation import PostgresRDSRelation  # noqa: F401
from dbt.adapters.postgresrds.impl import PostgresRDSAdapter

from dbt.adapters.base import AdapterPlugin
from dbt.include import postgresrds

Plugin = AdapterPlugin(
    adapter=PostgresRDSAdapter, credentials=PostgresRDSCredentials, include_path=postgresrds.PACKAGE_PATH
)
