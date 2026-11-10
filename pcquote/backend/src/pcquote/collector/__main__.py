"""Collector command line.

    uv run python -m pcquote.collector run [--expand] [--daily] [--prices-only | --benchmarks-only]
                                           [--refresh-benchmarks] [--reparse-cache] [--benchmark-archive PATH] [--publish]
    uv run python -m pcquote.collector daily [--check] [--force]   # nightly job (LaunchAgent)
    uv run python -m pcquote.collector expand
    uv run python -m pcquote.collector publish                    # rebuild the snapshot from stored observations
    uv run python -m pcquote.collector discover 삼성전자 990 EVO Plus 2TB
    uv run python -m pcquote.collector bootstrap [--with-cache]   # copy buildmate's Node collector state
    uv run python -m pcquote.collector shadow                     # bootstrap + replay Node's pages + compare catalogs
    uv run python -m pcquote.collector cutover                    # the collector starts publishing the server catalog

Exit codes: 0 succeeded, 2 partial (missing / stale / source errors), 1 failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import quote

from pathlib import Path

from pcquote import importer, llm
from pcquote.collector.client import SourceClient
from pcquote.collector.store import PgPageCache, PipelineStore
from pcquote.db import create_schema, put_document


def _print(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m pcquote.collector")
    sub = ap.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    for flag in ("--expand", "--daily", "--prices-only", "--benchmarks-only", "--refresh-benchmarks", "--reparse-cache", "--publish"):
        run.add_argument(flag, action="store_true")
    run.add_argument("--benchmark-archive")
    d = sub.add_parser("daily")
    d.add_argument("--check", action="store_true")
    d.add_argument("--force", action="store_true")
    sub.add_parser("expand")
    sub.add_parser("publish")
    disc = sub.add_parser("discover")
    disc.add_argument("query", nargs="+")
    boot = sub.add_parser("bootstrap")
    boot.add_argument("--with-cache", action="store_true")
    sub.add_parser("shadow")
    sub.add_parser("cutover")
    args = ap.parse_args(argv)

    create_schema()
    llm.load_env_files([Path(__file__).resolve().parents[3] / ".env", importer.BUILDMATE / ".env"])  # NAVER_* keys
    store = PipelineStore()
    try:
        if args.command == "run":
            from pcquote.collector.run import run_pipeline

            options = {k: v for k, v in vars(args).items() if k != "command"}
            if not args.publish:
                options["publish"] = None  # follow the catalog owner
            result = run_pipeline(options, store=store)
            return 2 if result["status"] == "partial" else 0
        if args.command == "daily":
            from pcquote.collector.daily import daily

            _print(daily(store, check=args.check, force=args.force))
            return 0
        if args.command == "expand":
            from pcquote.collector.expand import expand_catalog

            _print(expand_catalog(store, SourceClient(cache=PgPageCache()), on_progress=lambda v: None))
            return 0
        if args.command == "publish":
            from pcquote.collector.run import publish_catalog

            snapshot = publish_catalog(store)
            _print({"stage": "published", "total": snapshot["coverage"]["total"], "ready": snapshot["coverage"]["ready"],
                    "version": snapshot["catalogVersion"]})
            return 0
        if args.command == "discover":
            from pcquote.collector.parse import parse_search

            query = " ".join(args.query)
            page = SourceClient(cache=PgPageCache()).text("https://search.danawa.com/?query=" + quote(query))
            _print({"query": query, "collectedAt": page["fetchedAt"], "candidates": parse_search(page["text"])[:20],
                    "next": "용량·키트·VRAM·유통 형태를 확인한 후 등록하세요."})
            return 0
        if args.command == "bootstrap":
            from pcquote.collector.bootstrap import bootstrap
            from pcquote.collector.run import DATA_DIR

            _print(bootstrap(store, with_cache=args.with_cache, data_dir=DATA_DIR))
            return 0
        if args.command == "shadow":
            from pcquote.collector.shadow import shadow

            report = shadow(store)
            _print(report)
            return 0 if report["equal"] else 1
        if args.command == "cutover":
            from pcquote.collector.run import OWNER_DOC

            put_document(store.s, OWNER_DOC, {"owner": "collector"})
            store.s.commit()
            _print({"owner": "collector"})
            return 0
    finally:
        store.close()
    return 1


if __name__ == "__main__":
    sys.exit(main())
