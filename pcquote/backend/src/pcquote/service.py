"""Catalog state shared by the API: the screen's snapshot and the engine's ``Catalog`` from one load.

Loads PostgreSQL rows (importing a newly published pipeline snapshot first),
keeps them in memory for ``TTL_SECONDS``, and applies live price refreshes.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from . import importer, policy
from .catalog import CATEGORIES, Catalog, Part
from .db import (
    PartRow,
    PriceHistoryRow,
    PriceObservationRow,
    PriceReviewRow,
    ReviewQueueRow,
    get_document,
    put_document,
    session_factory,
)

TTL_SECONDS = 300
PRICE_REVIEW_RATIO = 0.30


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass
class State:
    meta: dict
    parts: dict[str, dict]  # id → screen-format part (raw), including OS and virtual options
    catalog: Catalog
    loaded_at: datetime
    _body: bytes | None = None

    @property
    def version(self) -> str | None:
        return self.meta.get("catalogVersion")

    def snapshot_bytes(self) -> bytes:
        """``GET /api/catalog`` body, serialized once per load (the screen polls it every minute)."""
        if self._body is None:
            self._body = json.dumps({**self.meta, "parts": list(self.parts.values())}, ensure_ascii=False).encode()
        return self._body


def engine_part(row: PartRow, now: datetime) -> Part | None:
    if row.category not in CATEGORIES or not row.raw or row.raw.get("virtual") or row.price <= 0:
        return None
    return Part(
        id=row.id, category=row.category, name=row.name, brand=row.brand, price=row.price, in_stock=row.in_stock,
        specs=row.specs or {}, benchmark=row.benchmark, benchmark_name=row.benchmark_name, source_url=row.source_url,
        price_observed_at=row.price_observed_at, popularity_rank=row.popularity_rank,
        popularity_observed_at=row.popularity_observed_at, quotable=not policy.policy_issue(row.raw, now),
    )


class PriceReviewPending(Exception):
    pass


class CatalogService:
    def __init__(self, sync_source: bool = True):
        self._state: State | None = None
        self._loaded = 0.0
        self._lock = RLock()
        self.sync_source = sync_source

    def get(self) -> State:
        with self._lock:
            if self._state is None or time.monotonic() - self._loaded > TTL_SECONDS:
                self._state = self._load()
                self._loaded = time.monotonic()
            return self._state

    def invalidate(self) -> None:
        with self._lock:
            self._state = None

    def _load(self) -> State:
        now = utcnow()
        with session_factory()() as s:
            if self.sync_source:
                importer.sync(s)
            rows = s.scalars(select(PartRow).where(PartRow.raw.is_not(None))).all()
            meta = get_document(s, "catalog-meta") or {"schemaVersion": 2, "mode": "live", "catalogVersion": None}
        parts = {r.id: r.raw for r in rows}
        engine = [p for p in (engine_part(r, now) for r in rows) if p]
        return State(meta=meta, parts=parts, catalog=Catalog(engine, now=now), loaded_at=now)

    # --- live price refresh ---------------------------------------------------

    def accept_price(self, part_id: str, observation: dict) -> None:
        """Store a collected price; a move over 30% from the last observation waits for staff review."""
        observed = datetime.fromisoformat(observation["observedAt"].replace("Z", "+00:00"))
        with self._lock, session_factory()() as s:
            row = s.get(PartRow, part_id)
            if row is None or row.raw is None:
                raise KeyError(part_id)
            prior = s.scalars(select(PriceHistoryRow).where(PriceHistoryRow.part_id == part_id)
                              .order_by(PriceHistoryRow.observed_at.desc(), PriceHistoryRow.id.desc()).limit(1)).first()
            amount = observation["amount"]
            if prior and prior.price > 0 and abs(amount / prior.price - 1) > PRICE_REVIEW_RATIO:
                exists = s.scalars(select(PriceReviewRow).where(PriceReviewRow.part_id == part_id,
                                                                PriceReviewRow.evidence_hash == observation["hash"])).first()
                if not exists:
                    # Same staff queue as the nightly collector, so the pipeline status shows it.
                    s.execute(pg_insert(ReviewQueueRow).values(
                        id=str(uuid.uuid4()), kind="price", part_id=part_id, reason="직전 가격 대비 30% 이상 변동: 담당자 확인 필요",
                        evidence_hash=observation["hash"], payload={"prior": {"amount": prior.price, "observedAt": iso(prior.observed_at)},
                                                                    "price": observation},
                        created_at=utcnow(), status="pending").on_conflict_do_nothing())
                    s.add(PriceReviewRow(part_id=part_id, reason="직전 가격 대비 30% 이상 변동: 담당자 확인 필요",
                                         evidence_hash=observation["hash"],
                                         payload={"prior": {"amount": prior.price, "observedAt": iso(prior.observed_at)},
                                                  "price": observation}))
                    s.commit()
                raise PriceReviewPending("가격 변동 검수 대기")
            in_stock = observation.get("availability") != "out-of-stock"
            row.price, row.price_observed_at, row.in_stock = amount, observed, in_stock
            row.raw = {**row.raw, "price": amount, "priceEvidence": observation, "observedAt": observation["observedAt"],
                       "inStock": in_stock}
            s.add(PriceHistoryRow(part_id=part_id, price=amount, observed_at=observed, source="danawa-refresh"))
            # The collector's next 30% check compares against this observation.
            s.execute(pg_insert(PriceObservationRow).values(
                part_id=part_id, amount=amount, source_url=observation["sourceUrl"], observed_at=observed,
                evidence_hash=observation["hash"], payload=observation).on_conflict_do_nothing())
            meta = get_document(s, "catalog-meta") or {}
            meta = {**meta, "catalogVersion": hashlib.sha256(
                json.dumps([meta.get("catalogVersion"), part_id, amount, observation["observedAt"]]).encode()).hexdigest()[:20]}
            put_document(s, "catalog-meta", meta)
            s.commit()
            self.invalidate()


def latest_meta(session: Session) -> dict:
    return get_document(session, "catalog-meta") or {}
