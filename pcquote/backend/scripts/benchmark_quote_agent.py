"""Live latency check: uv run python scripts/benchmark_quote_agent.py '사무용 PC 100만원'."""
import argparse
import asyncio
import json
import time
from pathlib import Path

from pcquote.collector.store import PgPageCache
from pcquote.danawa import collect_price, quote_source_client
from pcquote.llm import load_env_files
from pcquote.quote_agent import AgentRequest, create_quote
from pcquote.service import CatalogService


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('text', nargs='?', default='사무용 PC 100만원')
    parser.add_argument('--max-seconds', type=float, default=15)
    args = parser.parse_args()
    backend = Path(__file__).resolve().parents[1]
    load_env_files([backend / '.env', backend.parent.parent / 'buildmate' / '.env'])
    source = quote_source_client(cache=PgPageCache())
    start = time.monotonic()
    try:
        result = await create_quote(AgentRequest(text=args.text), CatalogService(), lambda p: collect_price(source, p))
    finally:
        source.http.close()
    elapsed = time.monotonic() - start
    quote = result.get('quote', {})
    plans = [p for p in quote.get('plans', []) if p]
    print(json.dumps({'seconds': round(elapsed, 2), 'status': result['status'], 'plans': len(plans),
                      'refresh': quote.get('refresh'), 'totals': [p['total'] for p in plans]}, ensure_ascii=False))
    if not plans or elapsed > args.max_seconds:
        raise SystemExit(1)


if __name__ == '__main__':
    asyncio.run(main())
