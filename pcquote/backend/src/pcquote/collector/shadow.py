"""Shadow check: run the Python collector on the pages the Node collector fetched and compare the catalogs.

No network: pages come from buildmate's cache (ReplayClient) and benchmarks from
buildmate's Blender archive. Fields that depend on the moment of evaluation
(price / benchmark status, coverage, versions) are left out of the comparison.
"""

from __future__ import annotations

import collections
import sqlite3

from pcquote.collector.bootstrap import ReplayClient, bootstrap, read_buildmate_doc
from pcquote.collector.run import run_pipeline
from pcquote.collector.store import PipelineStore
from pcquote.importer import BUILDMATE, CATALOG_DOC, documents_db

VOLATILE = {"priceStatus", "benchmarkStatus"}


def same(a, b) -> bool:
    """Equal, treating floats within 1e-12 relative as equal (Python versions sum floats differently)."""
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= 1e-12 * max(abs(a), abs(b), 1e-300)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def compare_catalogs(node: dict, python: dict, limit: int = 3) -> dict:
    a = {p["id"]: p for p in node["parts"]}
    b = {p["id"]: p for p in python["parts"]}
    fields, examples = collections.Counter(), collections.defaultdict(list)
    for pid in sorted(set(a) & set(b)):
        for key in sorted((set(a[pid]) | set(b[pid])) - VOLATILE):
            if not same(a[pid].get(key, "<absent>"), b[pid].get(key, "<absent>")):
                fields[key] += 1
                if len(examples[key]) < limit:
                    examples[key].append({"id": pid, "node": a[pid].get(key, "<absent>"), "python": b[pid].get(key, "<absent>")})
    only_node, only_python = sorted(set(a) - set(b)), sorted(set(b) - set(a))
    return {"parts": {"node": len(a), "python": len(b)}, "onlyNode": only_node[:20], "onlyPython": only_python[:20],
            "differentFields": dict(fields), "examples": dict(examples),
            "equal": not fields and not only_node and not only_python}


def shadow(store: PipelineStore, root=BUILDMATE) -> dict:
    copied = bootstrap(store, root)
    client = ReplayClient(root)
    archive = documents_db(root).parent / "blender-latest.zip"
    result = run_pipeline({"publish": False, "benchmark_archive": str(archive)}, store=store, client=client, log=lambda v: None)
    with sqlite3.connect(f"file:{documents_db(root)}?mode=ro", uri=True) as conn:
        node = read_buildmate_doc(conn, CATALOG_DOC, root)
    report = compare_catalogs(node, result["snapshot"])
    return {"bootstrap": copied, "replayMisses": client.misses, "status": result["status"],
            "nodeGeneratedAt": node.get("generatedAt"), **report}
