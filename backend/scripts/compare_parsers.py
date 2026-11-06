"""Compare the Python Danawa parsers with buildmate's JavaScript on every cached real page.

    node scripts/dump_js_parsers.mjs ../../buildmate js.jsonl
    uv run python scripts/compare_parsers.py js.jsonl [--limit N]

Prints the number of pages compared, the differences per field, and a few examples.
"""

from __future__ import annotations

import argparse
import collections
import json
import sqlite3
import time

from pcquote.collector.parse import SourceError, benchmark_name, parse_popularity, parse_product, parse_search, valid_discovered
from pcquote.importer import BUILDMATE, documents_db


def canon(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def run(f):
    try:
        return {"ok": canon(f())}
    except SourceError as e:
        return {"error": str(e), "code": e.code}


def diff_fields(js, py, prefix=""):
    if isinstance(js, dict) and isinstance(py, dict):
        out = []
        for k in sorted(set(js) | set(py)):
            if k not in js or k not in py:
                out.append(f"{prefix}{k} (key {'py only' if k in py else 'js only'})")
            else:
                out += diff_fields(js[k], py[k], f"{prefix}{k}.")
        return out
    return [] if js == py else [prefix.rstrip(".")]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    conn = sqlite3.connect(f"file:{documents_db()}?mode=ro", uri=True)
    cache_dir = str(BUILDMATE / "backend/data/cache")
    counts, fields, examples = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    started = time.perf_counter()
    with open(args.jsonl) as f:
        for i, line in enumerate(f):
            if args.limit and i >= args.limit:
                break
            rec = json.loads(line)
            row = conn.execute("SELECT payload FROM documents WHERE path=?", (f"{cache_dir}/{rec['key']}.json",)).fetchone()
            page = json.loads(row[0])
            js_hash = ((rec["result"].get("ok") or {}).get("part") or {}).get("specSource", {}).get("hash") if rec["kind"] == "product" else None
            if rec["kind"] == "product" and js_hash and js_hash != page["hash"]:
                counts["changed since dump (skipped)"] += 1
                continue
            checks = {}
            if rec["kind"] == "product":
                result = run(lambda: parse_product(page["text"], rec["product"], page, allow_missing_price=True))
                checks["product"] = (rec["result"], result)
                if "ok" in result:
                    part = result["ok"]["part"]
                    checks["benchmarkName"] = (rec.get("benchmarkName"), benchmark_name(part["category"], part["name"]))
                    checks["validDiscovered"] = (rec.get("valid"), valid_discovered(part))
            else:
                checks["search"] = (rec["result"], run(lambda: parse_search(page["text"])))
                if "popularity" in rec:
                    checks["popularity"] = (rec["popularity"], run(lambda: parse_popularity(page["text"], rec["category"], page["url"], page["fetchedAt"])))
            for name, (js, py) in checks.items():
                counts[name] += 1
                if js != py:
                    counts[name + " diff"] += 1
                    for field in diff_fields(js, py) or ["(value)"]:
                        fields[f"{name}: {field}"] += 1
                        if len(examples[f"{name}: {field}"]) < 2:
                            examples[f"{name}: {field}"].append(rec["url"])
    print(json.dumps({"pages": i + 1, "seconds": round(time.perf_counter() - started), "checks": counts}, ensure_ascii=False, indent=1))
    for field, n in fields.most_common(40):
        print(f"{n:6d}  {field}  e.g. {examples[field]}")


if __name__ == "__main__":
    main()
