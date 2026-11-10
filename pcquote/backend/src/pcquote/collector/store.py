"""Collector store in PostgreSQL, ported from buildmate (pipeline/store.mjs).

Product facts, price and benchmark observations, jobs, the staff review queue, the
page cache and the collector's JSON documents (product registry, discovery state,
status reports). A price that moves more than 30% from the last accepted one is
queued for review instead of being stored.
"""

from __future__ import annotations

import hashlib
import uuid
import zlib
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from pcquote.collector.client import utc_iso
from pcquote.db import (
    BenchmarkObservationRow,
    CollectorJobRow,
    PriceObservationRow,
    ProductFactRow,
    ReviewQueueRow,
    SourceCacheRow,
    engine,
    get_document,
    put_document,
    session_factory,
)

PRICE_REVIEW_RATIO = 0.3
PREFIX = "collector/"


def _time(value: str) -> datetime:
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def now() -> datetime:
    return datetime.now(timezone.utc)


class Busy(Exception):
    """Another collector process holds the lock."""


@contextmanager
def advisory_lock(name: str):
    """Process-wide lock in PostgreSQL; released automatically if the process dies."""
    key = int.from_bytes(hashlib.sha256(f"pcquote-collector:{name}".encode()).digest()[:8], "big", signed=True)
    with engine().connect() as conn:
        if not conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar():
            raise Busy(name)
        try:
            yield
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
            conn.commit()


def lock_held(name: str) -> bool:
    try:
        with advisory_lock(name):
            return False
    except Busy:
        return True


class PipelineStore:
    def __init__(self, session: Session | None = None):
        self.s = session or session_factory()()

    def close(self) -> None:
        self.s.close()

    # Documents ---------------------------------------------------------------------------------
    def doc(self, name: str, default=None):
        value = get_document(self.s, PREFIX + name)
        return default if value is None else value

    def put_doc(self, name: str, value) -> None:
        put_document(self.s, PREFIX + name, value)
        self.s.commit()

    # Jobs --------------------------------------------------------------------------------------
    def start(self) -> str:
        job = str(uuid.uuid4())
        self.s.add(CollectorJobRow(id=job, started_at=now(), status="running"))
        self.s.commit()
        return job

    def finish(self, job: str, status: str, summary: dict) -> None:
        row = self.s.get(CollectorJobRow, job)
        row.finished_at, row.status, row.summary = now(), status, summary
        self.s.commit()

    def jobs(self) -> list[dict]:
        rows = self.s.scalars(select(CollectorJobRow).order_by(CollectorJobRow.started_at.desc()).limit(20))
        return [{"id": r.id, "started_at": utc_iso(r.started_at), "finished_at": r.finished_at and utc_iso(r.finished_at),
                 "status": r.status, "summary": r.summary} for r in rows]

    # Review queue ------------------------------------------------------------------------------
    def queue(self, kind: str, part_id: str | None, reason: str, evidence: str, payload: dict | None = None) -> None:
        self.s.execute(insert(ReviewQueueRow).values(id=str(uuid.uuid4()), kind=kind, part_id=part_id, reason=reason,
                                                     evidence_hash=evidence, payload=payload or {}, created_at=now(),
                                                     status="pending").on_conflict_do_nothing())
        self.s.commit()

    def reviews(self) -> list[dict]:
        rows = self.s.scalars(select(ReviewQueueRow).where(ReviewQueueRow.status == "pending")
                              .order_by(ReviewQueueRow.created_at.desc()).limit(200))
        return [{"id": r.id, "kind": r.kind, "part_id": r.part_id, "reason": r.reason, "created_at": utc_iso(r.created_at)} for r in rows]

    # Prices and facts --------------------------------------------------------------------------
    def latest_price(self, part_id: str) -> dict | None:
        row = self.s.scalar(select(PriceObservationRow.payload).where(PriceObservationRow.part_id == part_id)
                            .order_by(PriceObservationRow.observed_at.desc(), PriceObservationRow.id.desc()).limit(1))
        return row

    def _put_fact(self, part: dict, updated: datetime) -> None:
        stmt = insert(ProductFactRow).values(id=part["id"], payload=part, updated_at=updated)
        self.s.execute(stmt.on_conflict_do_update(index_elements=[ProductFactRow.id],
                                                  set_={"payload": stmt.excluded.payload, "updated_at": stmt.excluded.updated_at}))

    def record_price(self, price: dict) -> None:
        self.s.execute(insert(PriceObservationRow).values(
            part_id=price["partId"], amount=price["amount"], source_url=price["sourceUrl"], observed_at=_time(price["observedAt"]),
            evidence_hash=price["hash"], payload=price).on_conflict_do_nothing())

    def accept_product(self, observation: dict, reviews: dict | None = None) -> bool:
        part, price = observation["part"], observation["price"]
        prior = self.latest_price(part["id"])
        approved = (reviews or {}).get("approvedPriceHashes") or []
        if prior and prior.get("amount", 0) > 0 and abs(price["amount"] / prior["amount"] - 1) > PRICE_REVIEW_RATIO \
                and price["hash"] not in approved:
            self.queue("price", part["id"], "직전 가격 대비 30% 이상 변동: 담당자 확인 필요", price["hash"], {"prior": prior, "price": price})
            return False
        self._put_fact(part, _time(price["observedAt"]))
        self.record_price(price)
        self.s.commit()
        return True

    def record_product(self, part: dict) -> None:
        self._put_fact(part, now())
        self.s.commit()

    def _update_fact(self, part_id: str, changes: dict) -> None:
        row = self.s.get(ProductFactRow, part_id)
        if row:
            row.payload = {**row.payload, **changes}
            self.s.commit()

    def update_popularity(self, part_id: str, popularity: dict) -> None:
        self._update_fact(part_id, {"popularity": popularity})

    def update_listing_date(self, part_id: str, month, evidence) -> None:
        self._update_fact(part_id, {"listingMonth": month, "listingDateEvidence": evidence})

    def put_benchmark(self, part_id: str, value: dict) -> None:
        stmt = insert(BenchmarkObservationRow).values(part_id=part_id, payload=value, observed_at=_time(value["observedAt"]))
        self.s.execute(stmt.on_conflict_do_update(index_elements=[BenchmarkObservationRow.part_id],
                                                  set_={"payload": stmt.excluded.payload, "observed_at": stmt.excluded.observed_at}))
        self.s.commit()

    def products(self) -> list[dict]:
        latest = {r.part_id: r.payload for r in self.s.execute(text(
            "SELECT DISTINCT ON (part_id) part_id, payload FROM price_observations ORDER BY part_id, observed_at DESC, id DESC"))}
        benchmarks = {r.part_id: r.payload for r in self.s.scalars(select(BenchmarkObservationRow))}
        return [{**r.payload, "priceEvidence": latest.get(r.id), "benchmark": benchmarks.get(r.id)}
                for r in self.s.scalars(select(ProductFactRow))]

    def history(self, part_id: str, days: int = 90) -> list[dict]:
        rows = self.s.execute(select(PriceObservationRow.amount, PriceObservationRow.observed_at, PriceObservationRow.source_url)
                              .where(PriceObservationRow.part_id == part_id, PriceObservationRow.observed_at >= now() - timedelta(days=days))
                              .order_by(PriceObservationRow.observed_at))
        return [{"amount": a, "observed_at": utc_iso(t), "source_url": u} for a, t, u in rows]

    def histories(self, part_ids, days: int = 90) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {p: [] for p in part_ids}
        rows = self.s.execute(select(PriceObservationRow.part_id, PriceObservationRow.amount, PriceObservationRow.observed_at,
                                     PriceObservationRow.source_url)
                              .where(PriceObservationRow.observed_at >= now() - timedelta(days=days))
                              .order_by(PriceObservationRow.observed_at))
        for pid, a, t, u in rows:
            if pid in out:
                out[pid].append({"amount": a, "observed_at": utc_iso(t), "source_url": u})
        return out


class PgPageCache:
    """SourceClient page cache in PostgreSQL."""

    def __init__(self, factory=None):
        self.factory = factory or session_factory()

    @staticmethod
    def key(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()

    def get(self, url: str) -> dict | None:
        with self.factory() as s:
            row = s.get(SourceCacheRow, self.key(url))
            if not row:
                return None
            return {"url": row.url, "text": zlib.decompress(row.body).decode(), "fetchedAt": row.fetched_at, "hash": row.hash,
                    "etag": row.etag, "lastModified": row.last_modified}

    def put(self, page: dict) -> None:
        values = {"url_key": self.key(page["url"]), "url": page["url"], "body": zlib.compress(page["text"].encode(), 6),
                  "fetched_at": page["fetchedAt"], "hash": page["hash"], "etag": page.get("etag"), "last_modified": page.get("lastModified")}
        with self.factory() as s:
            stmt = insert(SourceCacheRow).values(**values)
            s.execute(stmt.on_conflict_do_update(index_elements=[SourceCacheRow.url_key],
                                                 set_={k: stmt.excluded[k] for k in values if k != "url_key"}))
            s.commit()


def clear_collector_tables(session: Session) -> None:
    for row in (CollectorJobRow, ProductFactRow, PriceObservationRow, BenchmarkObservationRow, ReviewQueueRow):
        session.execute(delete(row))
    session.commit()
