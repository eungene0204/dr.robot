"""Catalog import from the collection pipeline's published snapshot.

The Danawa/Blender collection pipeline (buildmate ``pipeline/``, a nightly batch
job) publishes ``public/data/catalog.json`` into buildmate's ``documents.db``.
This module copies that snapshot into PostgreSQL: engine fields for the
recommender plus the full record (``raw``) for the consultation screen.

A price already refreshed live (newer ``observedAt``) is never replaced by an
older snapshot value.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from . import policy
from .catalog import CATEGORIES
from .db import PartRow, PriceHistoryRow, get_document, put_document

BUILDMATE = Path(os.environ.get("BUILDMATE_ROOT", Path(__file__).resolve().parents[4] / "buildmate"))
SPEC_OVERRIDES = Path(__file__).resolve().parents[2] / "data/buildmate-reparsed-specs.json"
CATALOG_DOC = "public/data/catalog.json"

SPEC_KEYS = {
    "cpu": ["socket", "watts", "tdp", "igpu", "cores", "threads"],
    "board": ["socket", "ddr", "form", "slots", "maxRam", "m2", "wifi"],
    "ram": ["ddr", "capacity", "sticks", "speedMHz", "cl"],
    "gpu": ["watts", "vram", "length", "thicknessMm", "connector", "connectorCount", "minPsu"],
    "ssd": ["capacity", "m2", "readMBs", "writeMBs"],
    "psu": ["capacity", "connectors", "form", "efficiency"],
    "case": ["forms", "gpuLength", "gpuThickness", "expansionSlots", "coolerHeight", "color"],
    "cooler": ["sockets", "height", "coolingWatts", "color"],
}
PRICE_FIELDS = ("price", "priceEvidence", "inStock", "observedAt")


def _time(value) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) and value else None


def documents_db(root: Path = BUILDMATE) -> Path:
    return Path(os.environ.get("BUILDMATE_DATA_DIR", root / "backend/data")) / "documents.db"


def source_marker(root: Path = BUILDMATE) -> dict | None:
    """Identifies the current published snapshot without reading it."""
    db = documents_db(root)
    if db.exists():
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
            row = conn.execute("SELECT path, updated_at FROM documents WHERE path LIKE ?", (f"%{CATALOG_DOC}",)).fetchone()
        if row:
            return {"kind": "documents.db", "path": row[0], "updatedAt": row[1]}
    file = root / CATALOG_DOC
    if file.exists():
        return {"kind": "file", "path": str(file), "updatedAt": str(file.stat().st_mtime)}
    return None


def load_snapshot(marker: dict) -> dict:
    if marker["kind"] == "file":
        return json.loads(Path(marker["path"]).read_text(encoding="utf-8"))
    with sqlite3.connect(f"file:{documents_db()}?mode=ro", uri=True) as conn:
        row = conn.execute("SELECT payload FROM documents WHERE path = ?", (marker["path"],)).fetchone()
    return json.loads(row[0])


def load_snapshot_path(path: Path) -> dict:
    if path.suffix == ".db":
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
            row = conn.execute("SELECT payload FROM documents WHERE path LIKE ?", (f"%{CATALOG_DOC}",)).fetchone()
        if row is None:
            raise SystemExit(f"{path}: catalog document not found")
        return json.loads(row[0])
    return json.loads(path.read_text(encoding="utf-8"))


def ssd_interface(p: dict) -> str | None:
    return policy.ssd_interface(p)


def popularity(p: dict) -> tuple[int | None, datetime | None]:
    """Danawa category best-seller rank, only when it belongs to the part's own category."""
    pop = p.get("popularity") or {}
    if pop.get("category") != p.get("category") or pop.get("sort") != "BEST" or not isinstance(pop.get("rank"), int):
        return None, None
    return pop["rank"], _time(pop.get("observedAt"))


def convert(p: dict) -> dict | None:
    """Engine row for a published part; OS and virtual options stay in ``raw`` only."""
    category = p.get("category")
    if category not in CATEGORIES or p.get("virtual") or not isinstance(p.get("price"), int) or p["price"] <= 0:
        return None
    bench = p.get("benchmark") or {}
    measured = category in ("cpu", "gpu") and (bench.get("samples") or 0) >= 3 and bench.get("normalizedScore")
    evidence = p.get("priceEvidence") or {}
    rank, rank_at = popularity(p)
    specs = {k: p.get(k) for k in SPEC_KEYS[category] if p.get(k) is not None}
    if category == "ssd" and ssd_interface(p):
        specs["interface"] = ssd_interface(p)
    return {
        "id": p["id"], "category": category, "name": p["name"],
        "brand": p.get("brand") if isinstance(p.get("brand"), str) else None,
        "price": p["price"], "in_stock": p.get("inStock") is not False, "specs": specs,
        "benchmark": float(bench["normalizedScore"]) if measured else None,
        "benchmark_name": p.get("benchmarkName"),
        "source_url": p.get("sourceUrl") or evidence.get("sourceUrl"),
        "price_observed_at": _time(evidence.get("observedAt") or p.get("observedAt")),
        "popularity_rank": rank, "popularity_observed_at": rank_at,
    }


def import_snapshot(session: Session, snapshot: dict, *, source: dict | None = None,
                    overrides: Path | None = SPEC_OVERRIDES) -> dict:
    if snapshot.get("schemaVersion") != 2 or not isinstance(snapshot.get("parts"), list):
        raise ValueError("카탈로그 스냅샷 형식이 올바르지 않습니다.")
    fixes = json.loads(overrides.read_text(encoding="utf-8")) if overrides and overrides.exists() else {}
    existing = {r.id: r for r in session.scalars(select(PartRow))}
    seen_history = set(session.execute(select(PriceHistoryRow.part_id, PriceHistoryRow.observed_at)).all())
    rows, kept, history = [], [], []
    for raw in snapshot["parts"]:
        part = dict(raw)
        for key, value in fixes.get(part["id"], {}).items():
            if part.get(key) is None:  # fill only what the snapshot is missing
                part[key] = value
        prior = existing.get(part["id"])
        incoming = _time((part.get("priceEvidence") or {}).get("observedAt"))
        if prior and prior.raw and prior.price_observed_at and (incoming is None or incoming < prior.price_observed_at):
            part.update({k: prior.raw[k] for k in PRICE_FIELDS if k in prior.raw})
            kept.append([part["id"], prior.raw.get("price"), str(prior.price_observed_at)])
        row = convert(part) or {
            "id": part["id"], "category": part["category"], "name": part.get("name", ""), "brand": None,
            "price": part.get("price") if isinstance(part.get("price"), int) else 0, "in_stock": part.get("inStock") is not False,
            "specs": {}, "benchmark": None, "benchmark_name": None, "source_url": None, "price_observed_at": None,
            "popularity_rank": None, "popularity_observed_at": None,
        }
        row["raw"] = part
        rows.append(row)
        if row["price_observed_at"] and row["price"] > 0 and (row["id"], row["price_observed_at"]) not in seen_history:
            history.append({"part_id": row["id"], "price": row["price"], "observed_at": row["price_observed_at"],
                            "source": "pipeline-snapshot"})
    stmt = insert(PartRow)
    session.execute(stmt.on_conflict_do_update(index_elements=[PartRow.id],
                                               set_={c: stmt.excluded[c] for c in rows[0] if c != "id"}), rows)
    ids = {r["id"] for r in rows}
    for gone in set(existing) - ids:  # dropped from the catalog: keep price history, hide from quotes
        existing[gone].raw = None
        existing[gone].in_stock = False
    session.flush()
    if history:
        session.execute(insert(PriceHistoryRow), history)
    meta = {k: v for k, v in snapshot.items() if k != "parts"}
    if kept:
        meta["catalogVersion"] = hashlib.sha256(json.dumps([meta.get("catalogVersion"), kept]).encode()).hexdigest()[:20]
    put_document(session, "catalog-meta", meta)
    if source:
        put_document(session, "catalog-source", source)
    session.commit()
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    return {"parts": counts, "keptNewerPrices": len(kept), "removed": len(set(existing) - ids)}


def sync(session: Session, root: Path = BUILDMATE, force: bool = False) -> dict | None:
    """Import buildmate's published snapshot when it changed since the last import.

    After cutover the Python collector publishes directly and buildmate's snapshot is ignored.
    """
    if (get_document(session, "catalog-owner") or {}).get("owner") == "collector":
        return None
    marker = source_marker(root)
    if marker is None or (not force and get_document(session, "catalog-source") == marker):
        return None
    return import_snapshot(session, load_snapshot(marker), source=marker)
