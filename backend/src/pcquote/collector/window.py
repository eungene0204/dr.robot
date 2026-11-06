"""Two-year collection window in Korea time (buildmate pipeline/window.mjs)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SEOUL = ZoneInfo("Asia/Seoul")


def seoul_day(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).astimezone(SEOUL).strftime("%Y-%m-%d")


def collection_window(now: datetime | None = None, years: int = 2) -> dict:
    end = seoul_day(now)
    y, m, d = (int(x) for x in end.split("-"))
    y -= years
    if m == 2 and d == 29:  # JavaScript setUTCFullYear rolls Feb 29 over to Mar 1
        m, d = 3, 1
    return {"start": f"{y:04d}-{m:02d}-{d:02d}", "end": end, "years": years,
            "basis": "manufacturer-release-date; listing-month kept separately"}


def window_coverage(parts: list[dict], window: dict | None = None) -> dict:
    window = window or collection_window()
    counts = {"confirmedRelease": 0, "recentListing": 0, "boundaryListingMonth": 0, "olderListing": 0, "dateUnknown": 0}
    start_month = window["start"][:7]
    for p in parts:
        if p.get("virtual"):
            continue
        ev = p.get("releaseEvidence") or {}
        release = ev.get("date") if ev.get("reviewed") and ev.get("sourceUrl") else None
        if release and window["start"] <= release <= window["end"]:
            counts["confirmedRelease"] += 1
        month = p.get("listingMonth")
        if not (isinstance(month, str) and re.fullmatch(r"\d{4}-\d{2}", month)):
            counts["dateUnknown"] += 1
        elif month == start_month:
            counts["boundaryListingMonth"] += 1
        elif month > start_month:
            counts["recentListing"] += 1
        else:
            counts["olderListing"] += 1
    return {**window, **counts, "complete": False}
