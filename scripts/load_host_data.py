#!/usr/bin/env python

import gzip
import sys

from datetime import datetime
from datetime import timedelta
from pathlib import Path
from time import sleep
from uuid import uuid4

from app_common_python import json
from app_common_python import os
from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy import delete
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Session
from sqlalchemy.sql.ddl import CreateSchema
from sqlalchemy.types import JSON
from sqlalchemy.types import String
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.types import UUID

from roadmap.config import Settings


class HBI(DeclarativeBase):
    __table_args__ = {"schema": "hbi"}


class Host(HBI):
    __tablename__ = "hosts"

    id: Mapped[UUID] = mapped_column(UUID(), primary_key=True)
    account: Mapped[str | None] = mapped_column(String(30), nullable=True, default=None)
    display_name: Mapped[str] = mapped_column(String(200))
    created_on: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP())
    modified_on: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP())
    facts: Mapped[JSON] = mapped_column(JSON(), nullable=True, default={})
    tags: Mapped[JSON] = mapped_column(JSON(), nullable=True, default={})
    canonical_facts: Mapped[JSON] = mapped_column(JSON(), nullable=True, default={})
    system_profile_facts: Mapped[JSON] = mapped_column(JSON(), nullable=True, default={})
    ansible_host: Mapped[str] = mapped_column(String(255))
    stale_timestamp: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP())
    reporter: Mapped[str] = mapped_column(String(255))
    per_reporter_staleness: Mapped[JSON] = mapped_column(JSON(), default={})
    org_id: Mapped[str] = mapped_column(String(36))
    groups: Mapped[JSON] = mapped_column(JSON(), default=[])
    tags_alt: Mapped[JSON] = mapped_column(JSON(), nullable=True, default=[{}])
    last_check_in: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP())


def wait_for_database(engine):
    count = 0
    max = 10
    while count < max:
        try:
            engine.connect()
            return
        except Exception:
            print("Waiting for database connection...")
            sleep(3)
            count += 1

    sys.exit("Unable to connect to database")


def get_host_data(data_file: Path):
    # Use data in the file to populate the database
    if data_file.suffix == ".gz":
        with gzip.open(data_file) as gzfile:
            host_data = json.load(gzfile)
    else:
        host_data = json.loads(data_file.read_bytes())

    return host_data


def main():
    fake = Faker()
    Faker.seed(8675309)  # Generate consistent data
    settings = Settings.create()
    engine = create_engine(str(settings.database_url), echo=True, pool_pre_ping=True, pool_timeout=60)
    wait_for_database(engine)
    with engine.connect() as connection:
        # Create the schema
        connection.execute(CreateSchema("hbi", if_not_exists=True))
        connection.commit()

    # Create the table and table schema
    Host.metadata.create_all(engine)

    # Allow overriding the host inventory data file
    data_file = Path(
        os.getenv(
            "ROADMAP_HOST_DATA_FILE",
            Path(__file__).parent.parent / "tests" / "fixtures" / "inventory_db_response.json.gz",
        ),
    )
    host_data = get_host_data(data_file)

    # Build the records
    records = []
    for n in range(len(host_data)):
        id = uuid4()
        init_date = fake.date_time_between(start_date="-1w")

        records.append(
            Host(
                id=id,
                display_name=fake.unique.hostname(),
                created_on=init_date,
                modified_on=init_date,
                system_profile_facts=host_data[n].get("system_profile_facts", {}),
                ansible_host="ansible_host",
                stale_timestamp=init_date + timedelta(30),
                reporter="toast loader",
                per_reporter_staleness={},
                org_id="1234",
                groups=[],
                tags_alt=[],
                last_check_in=datetime.now(),
            )
        )

    # Write the records to the database but first delete all existing records
    with Session(engine) as session:
        session.execute(delete(Host))
        session.add_all(records)
        session.commit()


if __name__ == "__main__":
    main()
