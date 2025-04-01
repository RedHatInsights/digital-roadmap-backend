#!/usr/bin/env python
# https://github.com/chambridge/replication_subscriber/blob/bea19ba28f7fb06b5401f1e7262456ec9bec40a7/replication_subscriber/runner.py
import logging
import os
import sys

from atexit import register
from functools import partial
from signal import SIGINT as CTRL_C_TERM
from signal import signal
from signal import Signals
from signal import SIGTERM as OPENSHIFT_TERM

import app_common_python

from sqlalchemy import create_engine
from sqlalchemy import text as sa_text
from sqlalchemy.orm import sessionmaker


__all__ = ("main", "run")

LOGGER_NAME = "replication-subscriber"
SSL_VERIFY_FULL = "verify-full"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


class ShutdownHandler:
    def __init__(self):
        self._shutdown = False

    def _signal_handler(self, signum, frame):
        signame = Signals(signum).name
        logger.info("Gracefully Shutting Down. Received: %s", signame)
        self._shutdown = True

    def register(self):
        signal(OPENSHIFT_TERM, self._signal_handler)
        signal(CTRL_C_TERM, self._signal_handler)

    def shut_down(self):
        return self._shutdown


def register_shutdown(function, message):
    def atexit_function():
        logger.info(message)
        function()

    register(atexit_function)


def _init_config():
    db_uri = None
    cfg = app_common_python.LoadedConfig
    if cfg and cfg.database:
        db_user = cfg.database.username
        db_password = cfg.database.password
        db_host = cfg.database.hostname
        db_port = cfg.database.port
        db_name = cfg.database.name
        if cfg.database.rdsCa:
            db_ssl_cert = cfg.rds_ca()
        db_ssl_mode = os.getenv("DB_SSL_MODE", "")
        db_uri = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        if db_ssl_mode == SSL_VERIFY_FULL:
            db_uri += f"?sslmode={db_ssl_mode}&sslrootcert={db_ssl_cert}"
    return db_uri


def _init_db(db_uri):
    engine = create_engine(db_uri)
    return sessionmaker(bind=engine), engine


def _excepthook(logger, type, value, traceback):
    logger.exception("Replication subcription job failed", exc_info=value)


def _db_exists(logger, session, sql):
    logger.debug(f"exists sql: {sql}")
    results = session.execute(sa_text(sql))
    rows = results.fetchall()
    return len(rows)


def check_or_create_view(logger, engine):
    view_template = """CREATE OR REPLACE VIEW hbi.hosts_view AS SELECT
        id,
        account,
        display_name,
        created_on as created,
        modified_on asupdated,
        stale_timestamp,
        stale_timestamp + INTERVAL '1' DAY * '7' AS stale_warning_timestamp,
        stale_timestamp + INTERVAL '1' DAY * '14' AS culled_timestamp,
        tags,
        system_profile_facts as system_profile,
        canonical_facts ->> 'insights_id'::text as insights_id,
        reporter,
        per_reporter_staleness,
        org_id,
        groups
    FROM hbi.hosts"""
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(sa_text(view_template))


def check_or_create_view_alt(logger, engine):
    view_template = """CREATE OR REPLACE VIEW hbi.hosts_alt_view AS SELECT
        id,
        account,
        display_name,
        created_on                                AS created,
        modified_on                               AS updated,
        stale_timestamp,
        stale_timestamp + INTERVAL '1' DAY * '7'  AS stale_warning_timestamp,
        stale_timestamp + INTERVAL '1' DAY * '14' AS culled_timestamp,
        COALESCE(
            (SELECT JSONB_AGG(
                        JSONB_BUILD_OBJECT(
                            'namespace', ns.namespace,
                            'key', k.key,
                            'value', v.value
                        )
                    )
                FROM JSONB_OBJECT_KEYS(tags) AS ns(namespace),
                    JSONB_EACH(tags -> ns.namespace) AS k(key, value),
                    JSONB_ARRAY_ELEMENTS_TEXT(k.value) AS v(value)),
            '[]'::jsonb
        )                                         AS tags,
        (SELECT JSONB_OBJECT_AGG(key, value)
            FROM JSONB_EACH(system_profile_facts)
            WHERE key IN (
                        'ansible',
                        'infrastructure_type',
                        'host_type',
                        'bootc_status',
                        'rhc_client_id',
                        'sap_sids',
                        'bios_release_date',
                        'system_update_method',
                        'bios_vendor',
                        'sap',
                        'sap_system',
                        'rhsm',
                        'owner_id',
                        'mssql',
                        'bios_version',
                        'operating_system'))       AS system_profile,
        (canonical_facts ->> 'insights_id')::uuid AS insights_id,
        reporter,
        per_reporter_staleness || JSONB_BUILD_OBJECT(
            'puptoo', per_reporter_staleness -> 'puptoo' || JSONB_BUILD_OBJECT(
                'stale_warning_timestamp',
                (per_reporter_staleness -> 'puptoo' ->> 'stale_timestamp')::timestamptz +
                INTERVAL '6 days',
                'culled_timestamp',
                (per_reporter_staleness -> 'puptoo' ->> 'stale_timestamp')::timestamptz +
                INTERVAL '13 days')
                                    )               AS per_reporter_staleness,
        org_id,
        groups
    FROM hbi.hosts"""
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(sa_text(view_template))


def check_or_create_indexes(logger, engine):
    db_indexes = [
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS hostas_account_index ON hbi.hosts (account)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS hosts_org_id_index ON hbi.hosts (org_id)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS hosts_display_name_index ON hbi.hosts (display_name)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS hosts_tags_index ON hbi.hosts USING GIN (tags JSONB_PATH_OPS)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS hosts_stale_timestamp_index ON hbi.hosts (stale_timestamp)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS hosts_system_profile_index ON hbi.hosts USING GIN (system_profile_facts JSONB_PATH_OPS)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS hosts_insights_id_index ON hbi.hosts USING btree (((canonical_facts ->> 'insights_id'::text)))",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS hosts_insights_reporter_index ON hbi.hosts (reporter)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS hosts_per_reporter_staleness_index ON hbi.hosts USING GIN (per_reporter_staleness JSONB_PATH_OPS)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS hosts_org_id_id_index ON hbi.hosts (org_id,id)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS hosts_groups_index ON hbi.hosts USING GIN (groups JSONB_PATH_OPS)",
    ]
    for db_index in db_indexes:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(sa_text(db_index))


def check_or_create_hosts_tables(logger, session):
    check_table = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'hbi' AND table_name ='hosts'"
    if not _db_exists(logger, session, check_table):
        logger.info("hbi.hosts not found.")
        hosts_table_create = """CREATE TABLE hbi.hosts (
            id uuid NOT NULL,
            account character varying(10),
            display_name character varying(200),
            created_on timestamp with time zone NOT NULL,
            modified_on timestamp with time zone NOT NULL,
            facts jsonb,
            tags jsonb,
            canonical_facts jsonb NOT NULL,
            system_profile_facts jsonb,
            ansible_host character varying(255),
            stale_timestamp timestamp with time zone NOT NULL,
            reporter character varying(255) NOT NULL,
            per_reporter_staleness jsonb DEFAULT '{}'::jsonb NOT NULL,
            org_id character varying(36) NOT NULL,
            groups jsonb NOT NULL
        );"""
        session.execute(sa_text(hosts_table_create))
        session.commit()
        logger.info("hbi.hosts created.")


def check_or_create_schema(logger, session, engine):
    check_schema = "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'hbi'"
    if not _db_exists(logger, session, check_schema):
        logger.info("hbi schema not found.")
        session.execute(sa_text("CREATE SCHEMA IF NOT EXISTS hbi"))
        session.commit()
        logger.info("hbi schema created.")
    check_or_create_hosts_tables(logger, session)
    check_or_create_indexes(logger, engine)
    check_or_create_view(logger, engine)
    check_or_create_view_alt(logger, engine)


def check_or_create_subscription(logger, session, engine):
    hbi_subscription = os.getenv("HBI_SUBSCRIPTION", "hbi_hosts_sub")
    check_subscription = "SELECT subname FROM pg_subscription WHERE subname = '" + hbi_subscription + "'"
    if _db_exists(logger, session, check_subscription):
        logger.debug(f"{hbi_subscription} found.")
        return
    logger.info(f"{hbi_subscription} not found.")
    hbi_file_list = [
        "/etc/db/hbi/db_host",
        "/etc/db/hbi/db_port",
        "/etc/db/hbi/db_name",
        "/etc/db/hbi/db_user",
        "/etc/db/hbi/db_password",
    ]
    if all(list(map(os.path.isfile, hbi_file_list))):
        logger.info("HBI secret files exist.")
        with open("/etc/db/hbi/db_host") as file:
            hbi_host = file.read().rstrip()
        with open("/etc/db/hbi/db_port") as file:
            hbi_port = file.read().rstrip()
        with open("/etc/db/hbi/db_name") as file:
            hbi_db_name = file.read().rstrip()
        with open("/etc/db/hbi/db_user") as file:
            hbi_user = file.read().rstrip()
        with open("/etc/db/hbi/db_password") as file:
            hbi_password = file.read().rstrip()
    db_ssl_mode = os.getenv("DB_SSL_MODE", "")
    ssl_connect = ""
    if db_ssl_mode and os.path.isfile("/etc/db/rdsclientca/rds_cacert"):
        ssl_connect = " sslmode=" + db_ssl_mode + " sslcert=/etc/db/rdsclientca/rds_cacert"
    hbi_publication = os.getenv("HBI_PUBLICATION", "hbi_hosts_pub")
    connection = (
        "'host="
        + hbi_host
        + " port="
        + hbi_port
        + " user="
        + hbi_user
        + " dbname="
        + hbi_db_name
        + " password="
        + hbi_password
    )
    connection += ssl_connect + "'"
    subscription_create = (
        "CREATE SUBSCRIPTION "
        + hbi_subscription
        + " CONNECTION "
        + connection
        + " PUBLICATION "
        + hbi_publication
        + ";"
    )
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(sa_text(subscription_create))
        logger.info(f"{hbi_subscription} created.")


def alter_subscription(logger, engine):
    alter_subscription = os.getenv("ALTER_SUBSCRIPTION")
    if not alter_subscription:
        return

    hbi_subscription = os.getenv("HBI_SUBSCRIPTION", "hbi_hosts_sub")
    alter_subscription_sql = "ALTER SUBSCRIPTION " + hbi_subscription + " " + alter_subscription
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(sa_text(alter_subscription_sql))
        logger.info(f"{hbi_subscription} altered to {alter_subscription}.")


def drop_subscription(logger, engine):
    drop_subscription = os.getenv("DROP_SUBSCRIPTION")
    if not drop_subscription:
        return

    hbi_subscription = os.getenv("HBI_SUBSCRIPTION", "hbi_hosts_sub")
    drop_subscription_sql = "DROP SUBSCRIPTION IF EXISTS " + hbi_subscription
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(sa_text(drop_subscription_sql))
        logger.info(f"{hbi_subscription} was dropped.")


def run(logger, session, engine):
    logger.info("Starting replication subcription runner")
    check_or_create_schema(logger, session, engine)
    check_or_create_subscription(logger, session, engine)
    alter_subscription(logger, engine)
    drop_subscription(logger, engine)
    logger.info("Finishing replication subcription runner")


def main(logger):
    db_uri = _init_config()
    Session, engine = _init_db(db_uri)
    session = Session()
    register_shutdown(session.get_bind().dispose, "Closing database")

    shutdown_handler = ShutdownHandler()
    shutdown_handler.register()
    run(logger, session, engine)


if __name__ == "__main__":
    logger = logging.getLogger(f"{LOGGER_NAME}")
    sys.excepthook = partial(_excepthook, logger)

    main(logger)
