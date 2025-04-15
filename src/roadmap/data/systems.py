from datetime import date

from roadmap.models import RHELLifecycle


# Mainline
# EUS - Extended Updated Support (73)
# E4S - Extended support for SAP
# ELS - Extended Lifecycle Support (204)
# EELS - Enhanced Extended Updated Support
#
# FIXME: This needs to be in the database
OS_LIFECYCLE_DATES = {
    "8": RHELLifecycle(
        major=8,
        start=date(2019, 5, 7),
        end=date(2029, 5, 31),
        end_els=date(2032, 5, 31),
    ),
    "8.0": RHELLifecycle(
        major=8,
        minor=0,
        start=date(2019, 5, 7),
        end=date(2019, 11, 30),
    ),
    "8.1": RHELLifecycle(
        major=8,
        minor=1,
        start=date(2019, 11, 5),
        end=date(2020, 5, 31),
        end_e4s=date(2023, 11, 30),
    ),
    "8.2": RHELLifecycle(
        major=8,
        minor=2,
        start=date(2020, 4, 28),
        end=date(2020, 10, 31),
        end_e4s=date(2024, 4, 30),
    ),
    "8.3": RHELLifecycle(
        major=8,
        minor=3,
        start=date(2020, 11, 3),
        end=date(2021, 5, 31),
    ),
    "8.4": RHELLifecycle(
        major=8,
        minor=4,
        start=date(2021, 5, 18),
        end=date(2021, 11, 30),
        end_eus=date(2023, 5, 31),
    ),
    "8.5": RHELLifecycle(
        major=8,
        minor=5,
        start=date(2021, 11, 9),
        end=date(2022, 5, 31),
    ),
    "8.6": RHELLifecycle(
        major=8,
        minor=6,
        start=date(2022, 5, 10),
        end=date(2022, 11, 30),
        end_eus=date(2024, 5, 31),
        end_e4s=date(2026, 5, 31),
    ),
    "8.7": RHELLifecycle(
        major=8,
        minor=7,
        start=date(2022, 11, 9),
        end=date(2023, 5, 31),
    ),
    "8.8": RHELLifecycle(
        major=8,
        minor=8,
        start=date(2023, 5, 16),
        end=date(2023, 11, 30),
        end_eus=date(2025, 5, 31),
        end_e4s=date(2027, 5, 31),
    ),
    "8.9": RHELLifecycle(
        major=8,
        minor=9,
        start=date(2023, 11, 14),
        end=date(2024, 5, 31),
    ),
    "8.10": RHELLifecycle(
        major=8,
        minor=10,
        start=date(2024, 5, 22),
        end=date(2029, 5, 31),
        end_els=date(2032, 5, 31),
    ),
    "9": RHELLifecycle(
        major=9,
        start=date(2022, 5, 18),
        end=date(2032, 5, 31),
        end_els=date(2035, 5, 31),
    ),
    "9.0": RHELLifecycle(
        major=9,
        minor=0,
        start=date(2022, 5, 18),
        end=date(2022, 11, 30),
        end_eus=date(2024, 5, 31),
        end_e4s=date(2026, 5, 31),
    ),
    "9.1": RHELLifecycle(
        major=9,
        minor=1,
        start=date(2022, 11, 15),
        end=date(2023, 5, 31),
    ),
    "9.2": RHELLifecycle(
        major=9,
        minor=2,
        start=date(2023, 5, 10),
        end=date(2023, 11, 30),
        end_eus=date(2025, 5, 31),
        end_e4s=date(2027, 5, 31),
    ),
    "9.3": RHELLifecycle(
        major=9,
        minor=3,
        start=date(2023, 11, 7),
        end=date(2024, 5, 31),
    ),
    "9.4": RHELLifecycle(
        major=9,
        minor=4,
        start=date(2024, 4, 30),
        end=date(2024, 10, 31),
        end_eus=date(2026, 4, 30),
        end_e4s=date(2028, 4, 30),
    ),
    "9.5": RHELLifecycle(
        major=9,
        minor=5,
        start=date(2024, 11, 12),
        end=date(2025, 5, 31),
    ),
    "9.6": RHELLifecycle(
        major=9,
        minor=6,
        start=date(2025, 5, 15),
        end=date(2025, 11, 30),
        end_eus=date(2027, 5, 30),
        end_e4s=date(2029, 5, 30),
    ),
    "9.7": RHELLifecycle(
        major=9,
        minor=7,
        start=date(2025, 11, 1),
        end=date(2026, 5, 31),
    ),
    "9.8": RHELLifecycle(
        major=9,
        minor=8,
        start=date(2026, 5, 15),
        end=date(2026, 11, 30),
        end_eus=date(2028, 5, 30),
        end_e4s=date(2030, 5, 30),
    ),
    "9.9": RHELLifecycle(
        major=9,
        minor=9,
        start=date(2026, 11, 1),
        end=date(2027, 5, 31),
    ),
    "9.10": RHELLifecycle(
        major=9,
        minor=10,
        start=date(2027, 5, 15),
        end=date(2032, 5, 31),
        end_els=date(2035, 5, 31),
    ),
    "10.1": RHELLifecycle(
        major=10,
        minor=1,
        start=date(2025, 11, 1),
        end=date(2026, 5, 31),
    ),
    "10.2": RHELLifecycle(
        major=10,
        minor=2,
        start=date(2026, 5, 15),
        end=date(2026, 11, 30),
        end_eus=date(2028, 5, 30),
        end_e4s=date(2030, 5, 30),
    ),
}
