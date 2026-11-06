"""Copy buildmate's Node collector state into PostgreSQL, and replay its cached pages.

`bootstrap` replaces the collector tables and documents with buildmate's current
pipeline.db / documents.db contents (read-only on buildmate). `ReplayClient` serves
pages from buildmate's page cache without touching the network, so the Python
collector can be run on exactly the pages the Node collector fetched.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import zlib
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, insert

from pcquote.collector.parse import SourceError
from pcquote.collector.store import PipelineStore, clear_collector_tables
from pcquote.db import (
    BenchmarkObservationRow,
    CollectorJobRow,
    PriceObservationRow,
    ProductFactRow,
    ReviewQueueRow,
    SourceCacheRow,
)
from pcquote.importer import BUILDMATE, documents_db

DOCUMENTS = {
    "products": "pipeline/config/products.json",
    "reviews": "pipeline/config/reviews.json",
    "discovery": "pipeline/config/discovery.json",
    "discovery-state": "{data}/discovery-state.json",
    "blender-meta": "{data}/blender-latest.zip.meta.json",
}


def _t(value: str | None) -> datetime | None:
    if not value:
        return None
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _path(template: str, root: Path) -> str:
    data = documents_db(root).parent
    return str(Path(template.format(data=data)) if template.startswith("{") else root / template)


def read_buildmate_doc(conn: sqlite3.Connection, template: str, root: Path):
    row = conn.execute("SELECT payload FROM documents WHERE path=?", (_path(template, root),)).fetchone()
    if row:
        return json.loads(row[0])
    file = Path(_path(template, root))
    return json.loads(file.read_text(encoding="utf-8")) if file.exists() else None


def bootstrap(store: PipelineStore, root: Path = BUILDMATE, *, with_cache: bool = False, data_dir: Path | None = None) -> dict:
    from pcquote.collector.run import collector_owns_catalog

    if collector_owns_catalog(store.s):
        raise RuntimeError("전환 후에는 Node 수집 상태로 덮어쓸 수 없습니다(수집기가 카탈로그를 발행 중).")
    data = documents_db(root).parent
    counts: dict[str, int] = {}
    with sqlite3.connect(f"file:{documents_db(root)}?mode=ro", uri=True) as docs:
        for name, template in DOCUMENTS.items():
            value = read_buildmate_doc(docs, template, root)
            if value is not None:
                store.put_doc(name, value)
                counts[f"doc:{name}"] = 1
    with sqlite3.connect(f"file:{data / 'pipeline.db'}?mode=ro", uri=True) as db:
        clear_collector_tables(store.s)
        s = store.s
        jobs = [{"id": i, "started_at": _t(a), "finished_at": _t(b), "status": st, "summary": json.loads(sm) if sm else None}
                for i, a, b, st, sm in db.execute("SELECT id, started_at, finished_at, status, summary FROM pipeline_jobs")]
        facts = [{"id": i, "payload": json.loads(p), "updated_at": _t(u)} for i, p, u in db.execute("SELECT id, payload, updated_at FROM product_facts")]
        prices = [{"part_id": pid, "amount": a, "source_url": url, "observed_at": _t(t), "evidence_hash": h, "payload": json.loads(p)}
                  for pid, a, url, t, h, p in db.execute(
                      "SELECT part_id, amount, source_url, observed_at, evidence_hash, payload FROM price_observations ORDER BY id")]
        benches = [{"part_id": pid, "payload": json.loads(p), "observed_at": _t(t)}
                   for pid, p, t in db.execute("SELECT part_id, payload, observed_at FROM benchmark_observations")]
        reviews = [{"id": i, "kind": k, "part_id": pid, "reason": r, "evidence_hash": h, "payload": json.loads(p), "created_at": _t(c),
                    "status": st or "pending"}
                   for i, k, pid, r, h, p, c, st in db.execute(
                       "SELECT id, kind, part_id, reason, evidence_hash, payload, created_at, status FROM review_queue")]
        for row, values in ((CollectorJobRow, jobs), (ProductFactRow, facts), (PriceObservationRow, prices),
                            (BenchmarkObservationRow, benches), (ReviewQueueRow, reviews)):
            for i in range(0, len(values), 2000):
                s.execute(insert(row), values[i:i + 2000])
            counts[row.__tablename__] = len(values)
        s.commit()
    archive = data / "blender-latest.zip"
    if data_dir and archive.exists():
        target = data_dir / "blender-latest.zip"
        if not target.exists() or target.stat().st_size != archive.stat().st_size:
            data_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(archive, target)
            counts["blenderArchive"] = 1
    if with_cache:
        counts["source_cache"] = copy_cache(store, root)
    return counts


def copy_cache(store: PipelineStore, root: Path = BUILDMATE) -> int:
    prefix = str(documents_db(root).parent / "cache") + "/"
    store.s.execute(delete(SourceCacheRow))
    n, batch = 0, []
    with sqlite3.connect(f"file:{documents_db(root)}?mode=ro", uri=True) as docs:
        for (payload,) in docs.execute("SELECT payload FROM documents WHERE path LIKE ?", (prefix + "%",)):
            page = json.loads(payload)
            if not isinstance(page.get("text"), str) or not isinstance(page.get("url"), str):
                continue
            batch.append({"url_key": hashlib.sha256(page["url"].encode()).hexdigest(), "url": page["url"],
                          "body": zlib.compress(page["text"].encode(), 6), "fetched_at": page["fetchedAt"], "hash": page["hash"],
                          "etag": page.get("etag"), "last_modified": page.get("lastModified")})
            if len(batch) >= 200:
                store.s.execute(insert(SourceCacheRow), batch)
                n += len(batch)
                batch = []
    if batch:
        store.s.execute(insert(SourceCacheRow), batch)
        n += len(batch)
    store.s.commit()
    return n


class ReplayClient:
    """SourceClient stand-in that answers from buildmate's page cache; never uses the network."""

    def __init__(self, root: Path = BUILDMATE):
        self.prefix = str(documents_db(root).parent / "cache")
        self.conn = sqlite3.connect(f"file:{documents_db(root)}?mode=ro", uri=True)
        self.misses = 0

    def text(self, url: str, **_) -> dict:
        key = hashlib.sha256(url.encode()).hexdigest()
        row = self.conn.execute("SELECT payload FROM documents WHERE path=?", (f"{self.prefix}/{key}.json",)).fetchone()
        if not row:
            self.misses += 1
            raise SourceError("재생 캐시에 없는 페이지", "replay_miss")
        return json.loads(row[0])

    def raw(self, url: str, **_):
        raise SourceError("재생 모드에서는 네트워크를 사용하지 않습니다.", "replay_network")
