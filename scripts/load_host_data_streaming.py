#!/usr/bin/env python3

import argparse
import os
import random

from datetime import datetime
from datetime import timedelta
from pathlib import Path
from time import sleep

from generate_hosts import iter_hosts
from load_host_data import HBI
from load_host_data import Host
from load_host_data import SystemProfileDynamic
from load_host_data import SystemProfileStatic
from sqlalchemy import create_engine
from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy.orm import Session
from sqlalchemy.sql.ddl import CreateSchema

from roadmap.config import Settings


DEFAULT_BATCH_SIZE = 100


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def parse_args() -> argparse.Namespace:
    default_input = Path(
        os.getenv(
            "ROADMAP_HOST_DATA_FILE",
            Path(__file__).parent.parent / "tests" / "fixtures" / "inventory_db_response.json.gz",
        )
    )
    parser = argparse.ArgumentParser(description="Stream HBI host data into the local database.")
    parser.add_argument("--input", type=Path, default=default_input, help="Hosts JSON file")
    parser.add_argument("--batch-size", type=positive_int, default=DEFAULT_BATCH_SIZE, help="Hosts per transaction")
    return parser.parse_args()


def wait_for_database(engine) -> None:
    for _ in range(10):
        try:
            with engine.connect():
                return
        except Exception:
            print("Waiting for database connection...")
            sleep(3)
    raise RuntimeError("Unable to connect to database")


def build_records(host: dict, randomizer: random.Random) -> tuple[dict, dict, dict]:
    host_id = host["id"]
    init_date = datetime.now() - timedelta(seconds=randomizer.randrange(7 * 24 * 60 * 60))
    system_profile = host.get("system_profile", {})

    host_record = {
        "id": host_id,
        "display_name": host.get("display_name") or str(host_id),
        "created_on": init_date,
        "modified_on": init_date,
        "ansible_host": "ansible_host",
        "stale_timestamp": init_date + timedelta(days=30),
        "reporter": "toast loader",
        "per_reporter_staleness": {},
        "org_id": "1234",
        "groups": host.get("groups", []),
        "tags_alt": [],
        "last_check_in": datetime.now(),
    }
    static_profile_record = {
        "host_id": host_id,
        "org_id": "1234",
        "operating_system": system_profile.get("operating_system", {}),
        "os_release": system_profile.get("os_release"),
        "dnf_modules": system_profile.get("dnf_modules", []),
    }
    dynamic_profile_record = {
        "host_id": host_id,
        "org_id": "1234",
        "installed_packages": system_profile.get("installed_packages", []),
        "installed_products": system_profile.get("installed_products", []),
    }
    return host_record, static_profile_record, dynamic_profile_record


def insert_batch(session: Session, records: tuple[list[dict], list[dict], list[dict]]) -> int:
    host_records, static_profile_records, dynamic_profile_records = records
    session.execute(insert(Host), host_records)
    session.execute(insert(SystemProfileStatic), static_profile_records)
    session.execute(insert(SystemProfileDynamic), dynamic_profile_records)
    session.commit()

    count = len(host_records)
    host_records.clear()
    static_profile_records.clear()
    dynamic_profile_records.clear()
    return count


def main() -> None:
    args = parse_args()
    data_file = args.input.resolve()
    if not data_file.is_file():
        raise SystemExit(f"Input file does not exist: {data_file}")

    engine = create_engine(str(Settings.create().database_url), pool_pre_ping=True, pool_timeout=60)
    try:
        wait_for_database(engine)
        with engine.begin() as connection:
            connection.execute(CreateSchema("hbi", if_not_exists=True))
        HBI.metadata.create_all(engine)

        with Session(engine) as session:
            session.execute(delete(SystemProfileDynamic))
            session.execute(delete(SystemProfileStatic))
            session.execute(delete(Host))
            session.commit()

            records: tuple[list[dict], list[dict], list[dict]] = ([], [], [])
            randomizer = random.Random(8675309)
            loaded = 0

            for host in iter_hosts(data_file):
                for batch, record in zip(records, build_records(host, randomizer), strict=True):
                    batch.append(record)
                if len(records[0]) == args.batch_size:
                    loaded += insert_batch(session, records)
                    if loaded % 10_000 == 0:
                        print(f"Loaded {loaded:,} hosts")

            if records[0]:
                loaded += insert_batch(session, records)
            print(f"Loaded {loaded:,} hosts from {data_file}")
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"Error: {error}") from error
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
