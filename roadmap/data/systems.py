from datetime import date

OS_DATA_MOCKED = [
    {
        "name": "RHEL",
        "major": 9,
        "minor": 2,
        "release": "Not applicable",
        "release_date": date(2023, 5, 1),
        "retirement_date": date(2023, 11, 1),
        "systems": 5,
        "lifecycle_type": "mainline",
    },
    {
        "name": "RHEL",
        "major": 8,
        "minor": 3,
        "release": "Not applicable",
        "release_date": date(2020, 11, 1),
        "retirement_date": date(2021, 5, 1),
        "systems": 50,
        "lifecycle_type": "eus",
    },
    {
        "name": "RHEL",
        "major": 8,
        "minor": 7,
        "release": "Not applicable",
        "release_date": date(2023, 5, 1),
        "retirement_date": date(2023, 5, 1),
        "systems": 12,
        "lifecycle_type": "e4s",
    },
    {
        "name": "RHEL",
        "major": 9,
        "minor": 0,
        "release": "Not applicable",
        "release_date": date(2022, 5, 18),
        "retirement_date": date(2032, 5, 1),
        "systems": 45,
        "lifecycle_type": "mainline",
    },
]
