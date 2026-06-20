"""A-share exchange closed dates (SSE/SZSE), excluding weekends.

Sources: SSE published holiday schedules; extend annually.
Weekends are handled separately in trading_calendar — this set is only statutory holidays.
"""

from __future__ import annotations

from datetime import date

# YYYY-MM-DD strings for days the exchange is closed on a weekday.
_A_SHARE_HOLIDAYS: frozenset[str] = frozenset(
    {
        # 2025
        "2025-01-01",
        "2025-01-28",
        "2025-01-29",
        "2025-01-30",
        "2025-01-31",
        "2025-02-03",
        "2025-02-04",
        "2025-04-04",
        "2025-05-01",
        "2025-05-02",
        "2025-05-05",
        "2025-05-31",
        "2025-06-02",
        "2025-10-01",
        "2025-10-02",
        "2025-10-03",
        "2025-10-06",
        "2025-10-07",
        "2025-10-08",
        # 2026
        "2026-01-01",
        "2026-01-02",
        "2026-02-16",
        "2026-02-17",
        "2026-02-18",
        "2026-02-19",
        "2026-02-20",
        "2026-02-23",
        "2026-04-06",
        "2026-05-01",
        "2026-05-04",
        "2026-05-05",
        "2026-06-19",  # 端午节
        "2026-06-20",
        "2026-06-21",
        "2026-10-01",
        "2026-10-02",
        "2026-10-05",
        "2026-10-06",
        "2026-10-07",
        "2026-10-08",
        # 2027 (partial; extend when calendar published)
        "2027-01-01",
    }
)


def is_exchange_holiday(d: date) -> bool:
    return d.isoformat() in _A_SHARE_HOLIDAYS
