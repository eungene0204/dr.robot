"""Collection pipeline status and manual runs.

Until cutover the buildmate Node batch job (``pipeline/run.mjs``) collects and writes
JSON documents into buildmate's ``documents.db``, read here read-only. After
``python -m pcquote.collector cutover`` the Python collector (``pcquote.collector``)
owns the catalog and its status documents live in PostgreSQL.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from threading import Lock

from .db import get_document, session_factory
from .importer import BUILDMATE, CATALOG_DOC, documents_db

BACKEND = Path(__file__).resolve().parents[2]


def collector_owns_catalog() -> bool:
    with session_factory()() as s:
        return (get_document(s, "catalog-owner") or {}).get("owner") == "collector"

DOCS = {
    "pipeline-status": ["{data}/pipeline-status.json", "{root}/public/data/pipeline-status.json"],
    "discovery-status": ["{root}/public/data/discovery-status.json"],
    "price-history": ["{root}/public/data/price-history.json"],
}


def read_doc(name: str, root: Path = BUILDMATE) -> dict | None:
    if collector_owns_catalog():
        with session_factory()() as s:
            return get_document(s, "collector/" + name)
    data_dir = documents_db(root).parent
    paths = [p.format(data=data_dir, root=root) for p in DOCS[name]]
    db = documents_db(root)
    if db.exists():
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
            for path in paths:
                row = conn.execute("SELECT payload FROM documents WHERE path = ?", (path,)).fetchone()
                if row:
                    return json.loads(row[0])
    for path in paths:
        if Path(path).exists():
            return json.loads(Path(path).read_text(encoding="utf-8"))
    return None


class PipelineRunner:
    def __init__(self, root: Path = BUILDMATE):
        self.root = root
        self.process: subprocess.Popen | None = None
        self._lock = Lock()

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self) -> bool:
        """Start a manual collection with discovery; False when a run is already in progress."""
        with self._lock:
            if self.running:
                return False
            if collector_owns_catalog():
                log = open(BACKEND / "data" / "collector.log", "a", encoding="utf-8")  # noqa: SIM115 — owned by the child process
                self.process = subprocess.Popen([sys.executable, "-m", "pcquote.collector", "run", "--expand"], cwd=BACKEND,
                                                stdout=log, stderr=log, stdin=subprocess.DEVNULL)
                return True
            node = shutil.which("node")
            if node is None:
                raise RuntimeError("수집 파이프라인 실행에 필요한 node를 찾을 수 없습니다.")
            data_dir = documents_db(self.root).parent
            log = open(data_dir / "pipeline.log", "a", encoding="utf-8")  # noqa: SIM115 — owned by the child process
            self.process = subprocess.Popen(
                [node, str(self.root / "pipeline/run.mjs"), "--expand", "--data-dir", str(data_dir),
                 "--output", str(self.root / CATALOG_DOC)],
                cwd=self.root, stdout=log, stderr=log, stdin=subprocess.DEVNULL)
            return True
