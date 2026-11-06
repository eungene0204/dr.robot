"""Nightly job: expand + collect once per Korea-time day, with a report (buildmate pipeline/daily.mjs)."""

from __future__ import annotations

import time
from datetime import datetime

from pcquote.collector.client import utc_iso
from pcquote.collector.store import Busy, PipelineStore, advisory_lock, lock_held
from pcquote.collector.window import seoul_day


def daily(store: PipelineStore, *, run=None, now: datetime | None = None, force: bool = False, check: bool = False,
          max_wait: float = 3 * 3600, poll: float = 10, sleep=time.sleep) -> dict:
    if run is None:
        from pcquote.collector.run import run_pipeline

        def run(options):
            return run_pipeline(options, store=store)

    day = seoul_day(now)
    name = f"daily-{day}"
    previous = store.doc(name)
    if check:
        return {"day": day, "timeZone": "Asia/Seoul", "schedule": "00:00", "previous": previous,
                "waitingForCollection": lock_held("expansion") or lock_held("pipeline")}
    if not force and (previous or {}).get("status") in ("succeeded", "partial"):
        return {"day": day, "status": "already-ran", "report": name}
    try:
        with advisory_lock("daily"):
            started = time.monotonic()
            report = {"day": day, "timeZone": "Asia/Seoul", "startedAt": utc_iso(), "status": "waiting"}
            try:
                store.put_doc(name, report)
                while lock_held("pipeline") or lock_held("expansion"):
                    if time.monotonic() - started >= max_wait:
                        raise TimeoutError("기존 수집 대기 3시간 초과")
                    sleep(poll)
                report.update(status="running", beforeProducts=len((store.doc("products") or {}).get("products") or []))
                store.put_doc(name, report)
                result = None
                while result is None:
                    try:
                        result = run({"expand": True, "daily": True})
                    except Busy:
                        if time.monotonic() - started >= max_wait:
                            raise RuntimeError("다른 수집 실행이 진행 중입니다.") from None
                        sleep(poll)
                after = sum(not p.get("virtual") for p in result["snapshot"]["parts"])
                report.update(status=result["status"], afterProducts=after, addedProducts=max(0, after - report["beforeProducts"]),
                              coverage=result["snapshot"]["coverage"], collectionWindow=result["snapshot"].get("collectionWindow"),
                              errors=result["summary"]["errors"], finishedAt=utc_iso())
                store.put_doc(name, report)
                return {**report, "report": name}
            except Exception as e:
                store.s.rollback()
                report.update(status="failed", error=str(e), finishedAt=utc_iso())
                store.put_doc(name, report)
                raise
    except Busy:
        return {"day": day, "status": "already-running"}
