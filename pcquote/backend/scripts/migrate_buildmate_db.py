"""Copy buildmate's SQLite operating data (buildmate.db) into PostgreSQL. Safe to re-run.

Copies issued quotes, store settings / theme / in-progress consultations, and LLM
usage. Existing rows are left as they are (quotes by id, settings by name).

    uv run python scripts/migrate_buildmate_db.py [path/to/buildmate.db]
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, insert, select

from pcquote.db import AppSettingRow, LlmUsageRow, SavedQuoteRow, create_schema, session_factory
from pcquote.importer import BUILDMATE


def _time(value: str) -> datetime:
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def migrate(path: Path) -> dict:
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
        quotes = conn.execute("SELECT id, created_at, payload FROM quotes").fetchall()
        settings = conn.execute("SELECT name, payload FROM app_settings").fetchall()
        usage = conn.execute("SELECT created_at, model, tokens, cost FROM llm_usage").fetchall()
    create_schema()
    with session_factory()() as s:
        known_quotes = set(s.scalars(select(SavedQuoteRow.id)))
        new_quotes = [{"id": i, "created_at": _time(c), "payload": json.loads(p)} for i, c, p in quotes if i not in known_quotes]
        if new_quotes:
            s.execute(insert(SavedQuoteRow), new_quotes)
        known_settings = set(s.scalars(select(AppSettingRow.name)))
        new_settings = [{"name": n, "payload": json.loads(p)} for n, p in settings if n not in known_settings]
        if new_settings:
            s.execute(insert(AppSettingRow), new_settings)
        q, st = len(new_quotes), len(new_settings)
        u = 0
        if usage and not s.scalar(select(func.count()).select_from(LlmUsageRow)):
            s.add_all(LlmUsageRow(created_at=_time(c), model=m, tokens=t, cost=cost) for c, m, t, cost in usage)
            u = len(usage)
        s.commit()
    return {"quotes": q, "settings": st, "llmUsage": u}


if __name__ == "__main__":
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else BUILDMATE / "backend/data/buildmate.db"
    print(f"migrating from {source}")
    print(migrate(source))
