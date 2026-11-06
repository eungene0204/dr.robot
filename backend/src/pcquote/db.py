"""PostgreSQL schema and catalog loading."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from functools import lru_cache

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    LargeBinary,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .catalog import Catalog, Part

DEFAULT_URL = "postgresql+psycopg:///pcquote"


class Base(DeclarativeBase):
    pass


class PartRow(Base):
    __tablename__ = "parts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(String(64))
    price: Mapped[int] = mapped_column(Integer)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    specs: Mapped[dict] = mapped_column(JSONB, default=dict)
    benchmark: Mapped[float | None] = mapped_column(Float)
    benchmark_name: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    price_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    popularity_rank: Mapped[int | None] = mapped_column(Integer)
    popularity_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw: Mapped[dict | None] = mapped_column(JSONB)  # full catalog record served to the consultation screen
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())

    def to_part(self) -> Part:
        return Part(
            id=self.id, category=self.category, name=self.name, brand=self.brand, price=self.price,
            in_stock=self.in_stock, specs=self.specs or {}, benchmark=self.benchmark,
            benchmark_name=self.benchmark_name, source_url=self.source_url,
            price_observed_at=self.price_observed_at, popularity_rank=self.popularity_rank,
            popularity_observed_at=self.popularity_observed_at,
        )


class PriceHistoryRow(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    part_id: Mapped[str] = mapped_column(ForeignKey("parts.id", ondelete="CASCADE"), index=True)
    price: Mapped[int] = mapped_column(Integer)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(32))


class SavedQuoteRow(Base):
    """Issued quote in the consultation screen's format (id, date, plan, req, settings, customerName…)."""

    __tablename__ = "saved_quotes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict] = mapped_column(JSONB)


class AppSettingRow(Base):
    """Store settings (``store``), theme and in-progress consultations (``consult-live``…)."""

    __tablename__ = "app_settings"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict | list | None] = mapped_column(JSONB)


class DocumentRow(Base):
    """Catalog metadata and other JSON documents (``catalog-meta``, ``catalog-source``)."""

    __tablename__ = "documents"

    name: Mapped[str] = mapped_column(String(128), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LlmUsageRow(Base):
    __tablename__ = "llm_usage"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    model: Mapped[str | None] = mapped_column(Text)
    tokens: Mapped[int | None] = mapped_column(Integer)
    cost: Mapped[float | None] = mapped_column(Float)


class PriceReviewRow(Base):
    """Price moves over 30% wait here for staff approval instead of entering the catalog."""

    __tablename__ = "price_reviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    part_id: Mapped[str] = mapped_column(String(64), index=True)
    reason: Mapped[str] = mapped_column(Text)
    evidence_hash: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Collector (ported from buildmate pipeline/store.mjs). Observations keep the source's exact
# payload; columns exist for ordering and uniqueness.


class CollectorJobRow(Base):
    __tablename__ = "collector_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))
    summary: Mapped[dict | None] = mapped_column(JSONB)


class ProductFactRow(Base):
    __tablename__ = "product_facts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PriceObservationRow(Base):
    __tablename__ = "price_observations"
    __table_args__ = (UniqueConstraint("part_id", "source_url", "observed_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    part_id: Mapped[str] = mapped_column(String(64), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    source_url: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    evidence_hash: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSONB)


class BenchmarkObservationRow(Base):
    __tablename__ = "benchmark_observations"

    part_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReviewQueueRow(Base):
    """Collector items waiting for staff: price moves over 30%, source errors, cross-source gaps."""

    __tablename__ = "review_queue"
    __table_args__ = (UniqueConstraint("kind", "part_id", "evidence_hash"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))
    part_id: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text)
    evidence_hash: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="pending")


class SourceCacheRow(Base):
    """Last fetched copy of each public page (zlib-compressed) for conditional requests and re-parsing."""

    __tablename__ = "source_cache"

    url_key: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256(url)
    url: Mapped[str] = mapped_column(Text)
    body: Mapped[bytes] = mapped_column(LargeBinary)
    fetched_at: Mapped[str] = mapped_column(String(32))  # exact ISO string; it becomes evidence time
    hash: Mapped[str] = mapped_column(String(64))
    etag: Mapped[str | None] = mapped_column(Text)
    last_modified: Mapped[str | None] = mapped_column(Text)


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_URL)


@lru_cache(maxsize=4)
def _engine(url: str):
    return create_engine(url, pool_pre_ping=True)


def engine():
    return _engine(database_url())


def session_factory() -> sessionmaker[Session]:
    return sessionmaker(engine(), expire_on_commit=False)


# Columns added after the first release; create_all does not alter existing tables.
_ADDED_COLUMNS = [
    "ALTER TABLE parts ADD COLUMN IF NOT EXISTS popularity_rank INTEGER",
    "ALTER TABLE parts ADD COLUMN IF NOT EXISTS popularity_observed_at TIMESTAMPTZ",
    "ALTER TABLE parts ADD COLUMN IF NOT EXISTS raw JSONB",
    "ALTER TABLE documents ALTER COLUMN name TYPE VARCHAR(128)",
]


def create_schema() -> None:
    Base.metadata.create_all(engine())
    with engine().begin() as conn:
        for ddl in _ADDED_COLUMNS:
            conn.execute(text(ddl))


def load_catalog(session: Session) -> Catalog:
    rows = session.scalars(select(PartRow)).all()
    return Catalog([r.to_part() for r in rows])


def get_document(session: Session, name: str) -> dict | None:
    row = session.get(DocumentRow, name)
    return row.payload if row else None


def put_document(session: Session, name: str, payload: dict) -> None:
    row = session.get(DocumentRow, name)
    if row:
        row.payload = payload
    else:
        session.add(DocumentRow(name=name, payload=payload))
