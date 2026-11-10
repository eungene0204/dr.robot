"""Price refresh for a single part at quote time.

Uses the collector's polite client and product-page parser (``pcquote.collector``),
so the screen's live refresh follows the same collection rules and produces the same
observation shape as the nightly collector.
"""

from __future__ import annotations

from pcquote.collector.client import AGENT, ALLOWED_HOSTS, SourceClient
from pcquote.collector.expand import collect_product
from pcquote.collector.parse import SourceError, parse_product

__all__ = ["AGENT", "ALLOWED_HOSTS", "SourceClient", "SourceError", "collect_price", "parse_price"]


def parse_price(html: str, part: dict, page: dict) -> dict:
    """Price observation from the product page's JSON-LD; raises SourceError when there is no valid KRW price."""
    product = {"id": part["id"], "category": part.get("category") or "cpu", "danawaPcode": part.get("danawaPcode")}
    return parse_product(html, product, page)["price"]


def collect_price(client: SourceClient, part: dict) -> dict:
    product = {"id": part["id"], "category": part.get("category") or "cpu", "danawaPcode": part.get("danawaPcode")}
    return collect_product(client, product)["price"]
