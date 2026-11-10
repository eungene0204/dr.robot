"""Danawa page parsers, ported from buildmate (pipeline/adapters/danawa.mjs, popularity.mjs, expand.mjs).

Results must equal the JavaScript parsers on the same page; tests/test_collector_parse.py
and scripts/compare_parsers.py check that against cached real pages.
"""

from __future__ import annotations

import json
import math
from urllib.parse import parse_qsl, urljoin, urlsplit

from selectolax.lexbor import LexborHTMLParser

from pcquote.collector.jsre import finite, js, js_number, js_string, js_values, num, safe_integer
from pcquote.policy import product_issues


class SourceError(Exception):
    def __init__(self, message: str, code: str = "source_error"):
        super().__init__(message)
        self.code = code


def _number(text: str, pattern: str, flags: str = ""):
    m = js(pattern, flags).search(text)
    return num(float(m.group(1).replace(",", ""))) if m else None


def _first(*values):
    """JavaScript a ?? b ?? c."""
    for v in values:
        if v is not None:
            return v
    return None


def _test(pattern: str, text: str, flags: str = "") -> bool:
    return js(pattern, flags).search(text) is not None


def detect_cooling_type(text: str = "") -> str:
    air = _test(r"공랭|air[ -]?cool(?:er|ing)?", text, "i")
    liquid = _test(r"수랭|수냉|liquid[ -]?cool(?:er|ing)?|water[ -]?cool(?:er|ing)?", text, "i")
    return "unknown" if air == liquid else "liquid" if liquid else "air"


def parse_specs(category: str, description: str, name: str = "") -> dict:
    text = js(r"\s+").sub(" ", description)
    spec: dict = {}
    m = js(r"소켓\s*(AM\d|LGA\s*\d+|\d{4})", "i").search(text) or js(r"\(\s*(AM\d|LGA\s*\d+|\d{4})\s*소켓\s*\)", "i").search(text)
    raw_socket = m.group(1).replace(" ", "") if m else None
    socket = f"LGA{raw_socket}" if raw_socket and js(r"^\d+$").search(raw_socket) else raw_socket
    capacity = _first(_number(text, r"(?:메모리 용량|용량)\s*:\s*(\d+)\s*GB", "i"), _number(name, r"(\d+)\s*GB", "i"))
    if category == "cpu":
        hybrid = js(r"P?\s*(\d+)\s*\+\s*E?\s*(\d+)\s*코어", "i").search(text)
        spec.update({
            "socket": socket or None,
            "watts": _first(_number(text, r"PBP\s*-\s*MTP\s*:\s*\d+\s*[-~]\s*(\d+)\s*W", "i"), _number(text, r"(?:PPT)\s*:\s*(\d+)\s*W", "i"),
                            _number(text, r"TDP\s*:\s*\d+\s*[-~]\s*(\d+)\s*W", "i"), _number(text, r"TDP\s*:\s*(\d+)\s*W", "i")),
            "tdp": _number(text, r"TDP\s*:\s*(\d+)\s*(?:[-~]\s*\d+\s*)?W", "i"),
            "igpu": False if _test(r"내장그래픽\s*:\s*미탑재|\/ 미탑재", text) else
            True if _test(r"Radeon|라데온|인텔 그래픽스|UHD\s*\d{3}|Iris\s*Xe|내장그래픽\s*:\s*(?:탑재|Intel)", text, "i") else None,
            "cores": int(hybrid.group(1)) + int(hybrid.group(2)) if hybrid else _number(text, r"(\d+)코어"),
            "threads": _number(text, r"(\d+)스레드"),
        })
    if category == "board":
        form = ("mATX" if _test(r"M[\s-]?ATX", text, "i") else "ITX" if _test(r"Mini[\s-]?ITX", text, "i")
                else "ATX" if _test(r"ATX", text, "i") else None)
        spec.update({
            "socket": socket or None,
            "ddr": _number(text, r"DDR\s*(\d)", "i"),
            "form": form,
            "slots": _first(_number(text, r"메모리 슬롯\s*:\s*(\d+)"), _number(text, r"메모리\]?\s*\/(?:[^/\[]+\/)*?\s*(\d+)개\s*\/\s*메모리 용량")),
            "maxRam": _number(text, r"(?:최대 메모리|메모리 용량|최대 용량)\s*:\s*(?:최대\s*)?(\d+)\s*GB", "i"),
            "m2": _number(text, r"M\.2\s*:\s*(\d+)개", "i"),
            "wifi": True if _test(r"Wi-Fi|WiFi|무선랜\s*:\s*탑재", text + " " + name, "i") else None,
            "bios": None,
        })
    if category == "ram":
        kit_re = js(r"(\d+)\s*GB\s*\(\s*(\d+)\s*G(?:B)?\s*[x×]\s*(\d+)\s*\)", "i")
        kit = kit_re.search(text) or kit_re.search(name)
        spec.update({
            "ddr": _number(text, r"DDR\s*(\d)", "i"),
            "capacity": int(kit.group(1)) if kit else capacity,
            "sticks": int(kit.group(3)) if kit else None if _test(r"패키지|키트", name) else 1,
            "speedMHz": _number(text, r"(\d{4,5})\s*MHz", "i"),
            "cl": _number(text, r"CL\s*(\d+)", "i"),
        })
    if category == "gpu":
        vram = _first(_number(text, r"(?:GDDR\d+[xX]?\s*\/\s*)(\d+)\s*GB", "i"), _number(name, r"(\d+)\s*GB", "i"))
        pm = js(r"전원 포트\s*:\s*([^/]+)").search(text)
        plug = pm.group(1) if pm else ""
        spec.update({
            "watts": _number(text, r"(?:사용전력|소비전력|최대 소비전력)\s*:\s*(\d+)\s*W", "i"),
            "vram": vram,
            "length": _number(text, r"(?:가로\(길이\)|가로|길이)\s*:\s*(\d+(?:\.\d+)?)\s*mm", "i"),
            "thickness": None,
            "thicknessMm": _number(text, r"두께\s*:\s*(\d+(?:\.\d+)?)\s*mm", "i"),
            "connector": "12v2x6" if _test(r"16핀", plug) else "8pin" if _test(r"8핀", plug) else None,
            "connectorCount": _number(plug, r"[x×]\s*(\d+)\s*$", "i"),
            "minPsu": _first(_number(text, r"정격파워\s*:\s*(\d+)\s*W", "i"), _number(text, r"(\d{3,4})\s*W\s*이상", "i")),
        })
    if category == "ssd":
        tb = _number(name, r"(\d+(?:\.\d+)?)\s*TB", "i")
        spec.update({
            "capacity": num(tb * 1000) if tb else capacity,
            "m2": 1 if _test(r"M\.2", text) else None,
            "readMBs": _number(text, r"순차읽기\s*:\s*([\d,]+)"),
            "writeMBs": _number(text, r"순차쓰기\s*:\s*([\d,]+)"),
        })
    if category == "psu":
        both = text + " " + name
        connectors = []
        if _test(r"PCIe\s*8핀|PCIe\s*6\+2핀|PCI-E\s*6\+2핀", text, "i"):
            connectors.append("8pin")
        if _test(r"12V[\s-]?2[x×]6", text, "i"):
            connectors.append("12v2x6")
        eff = js(r"80\s*PLUS\s*([^/]+)", "i").search(text)
        spec.update({
            "form": ("SFX-L" if _test(r"SFX[ -]?L", both, "i") else "SFX" if _test(r"SFX", both, "i")
                     else "TFX" if _test(r"TFX", both, "i") else "ATX" if _test(r"ATX", both, "i") else None),
            "capacity": _first(_number(text, r"(?:정격출력|출력)\s*:\s*(\d+)\s*W", "i"),
                               _number(text, r"(?:^|\/)\s*(\d{3,4})\s*W(?:\s*\/|$)", "i"), _number(name, r"(\d{3,4})\s*W", "i")),
            "connectors": connectors or None,
            "efficiency": (_js_trim(eff.group(1)) or None) if eff else None,
        })
    if category == "case":
        forms = []
        if _test(r"(?:^|[^A-Z-])ATX", text, "i"):
            forms.append("ATX")
        if _test(r"M[\s-]?ATX", text, "i"):
            forms.append("mATX")
        if _test(r"Mini[\s-]?ITX", text, "i"):
            forms.append("ITX")
        spec.update({
            "forms": forms or None,
            "gpuLength": _number(text, r"(?:VGA|GPU)(?: 장착)? (?:길이|최대길이)\s*:\s*(\d+)\s*mm", "i"),
            "gpuThickness": None,
            "expansionSlots": _number(text, r"(?:확장 슬롯|PCI 슬롯|PCIe 슬롯)\s*:\s*(\d+)", "i"),
            "coolerHeight": _number(text, r"CPU\s*쿨러\s*(?:장착)?\s*높이\s*:\s*(\d+)\s*mm", "i"),
            "color": "white" if _test(r"화이트|white", name, "i") else "black" if _test(r"블랙|black", name, "i") else None,
        })
    if category == "cooler":
        sockets = [s.replace(" ", "") for s in js(r"AM[45]|LGA\s*\d{4}", "i").findall(text)]
        spec.update({
            "coolingType": detect_cooling_type(text),
            "sockets": sockets or None,
            "height": _number(text, r"높이\s*:\s*(\d+(?:\.\d+)?)\s*mm", "i"),
            "coolingWatts": _number(text, r"TDP\s*:\s*(\d+)\s*W", "i"),
            "color": "white" if _test(r"화이트|white", name, "i") else None,
        })
    if category == "os":
        both = text + " " + name
        spec.update({"included": True, "licenseType": "FPP" if _test(r"FPP", both, "i") else "DSP" if _test(r"DSP", both, "i") else None})
    return spec


_TRIM = " \t\n\v\f\r                 　﻿"


def _js_trim(text: str) -> str:
    return text.strip(_TRIM)


def _url(href, base: str | None = None):
    """WHATWG-like URL parse: (hostname, first query value getter). Raises ValueError like `new URL` on relative input."""
    if not isinstance(href, str):
        href = js_string(href)
    href = _js_trim(href)
    full = urljoin(base, href) if base else href
    parts = urlsplit(full)
    if not parts.scheme or (parts.scheme in ("http", "https") and not parts.netloc):
        raise ValueError("invalid URL")
    params: dict[str, str] = {}
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        params.setdefault(k, v)
    return (parts.hostname or ""), params


_CATEGORY_NAMES = {"CPU": "cpu", "메인보드": "board", "RAM": "ram", "그래픽카드(GPU)": "gpu", "SSD": "ssd", "파워": "psu",
                   "케이스": "case", "쿨러/튜닝": "cooler"}


def _ld_json(tree: LexborHTMLParser):
    for el in tree.css('script[type="application/ld+json"]'):
        try:
            yield json.loads(el.text(deep=True))
        except ValueError:
            continue


def parse_product(html: str, product: dict, meta: dict, allow_missing_price: bool = False) -> dict:
    tree = LexborHTMLParser(html)
    data, breadcrumb = None, []
    for value in _ld_json(tree):
        items = value if isinstance(value, list) else [value, *((value.get("@graph") or []) if isinstance(value, dict) else [])]
        for v in items:
            if not isinstance(v, dict):
                continue
            if v.get("@type") == "Product" and js_string(v.get("sku")) == js_string(product.get("danawaPcode")):
                data = v
            if v.get("@type") == "BreadcrumbList":
                breadcrumb = [((x.get("item") or {}).get("name") if isinstance(x.get("item"), dict) else None) or x.get("name") or ""
                              for x in (v.get("itemListElement") or []) if isinstance(x, dict)]
    if not data or not isinstance(data.get("name"), str):
        raise SourceError("상품 SKU 또는 JSON-LD 구조가 일치하지 않습니다.", "schema_changed")
    offers = data.get("offers")
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    offers = offers if isinstance(offers, dict) else None
    raw_amount = offers.get("lowPrice") if offers and offers.get("lowPrice") is not None else (offers or {}).get("price")
    amount = js_number(raw_amount) if offers else math.nan
    offer_count = js_number(offers.get("offerCount")) if offers and "offerCount" in offers else math.nan
    has_price = bool(offers and offers.get("priceCurrency") == "KRW" and safe_integer(amount) and amount > 0 and offer_count != 0)
    if not has_price and not allow_missing_price:
        raise SourceError("유효한 KRW 판매가격이 없습니다.", "no_price")
    url = f"https://prod.danawa.com/info/?pcode={product['danawaPcode']}"
    source_category = next((_CATEGORY_NAMES[n] for n in breadcrumb if n in _CATEGORY_NAMES), None)
    description = data.get("description") or ""
    specs = parse_specs(product["category"], description, data["name"])
    for el in tree.css("script, style"):
        el.decompose()
    body = tree.body.text(deep=True) if tree.body else ""
    listing = js(r"등록월\s*[:：]\s*(\d{4})[.\/-]\s*(\d{1,2})").search(body)
    listing_month = f"{listing.group(1)}-{listing.group(2).zfill(2)}" if listing and 1 <= int(listing.group(2)) <= 12 else None
    evidence = ({"kind": "danawa-registration-month", "sourceUrl": url, "observedAt": meta["fetchedAt"], "hash": meta["hash"],
                 "precision": "month"} if listing_month else None)
    part = {**product, "name": data["name"]}
    # JSON.stringify drops undefined: a missing brand (or brand object without a name) leaves no key.
    brand = data.get("brand")
    if isinstance(brand, dict):
        if "name" in brand:
            part["brand"] = brand["name"]
    elif "brand" in data:
        part["brand"] = brand
    part.update({"listingMonth": listing_month, "listingDateEvidence": evidence, "sourceCategory": source_category,
                 "productType": _js_trim(description.split("/")[0]), **specs,
                 "specSource": {"url": url, "observedAt": meta["fetchedAt"], "hash": meta["hash"], "method": "product-jsonld", "reviewed": False}})
    price = None
    if has_price:
        price = {"partId": product["id"], "amount": amount, "currency": "KRW", "shipping": None, "shippingKnown": False, "source": "danawa",
                 "sourceUrl": url, "seller": "다나와 가격비교", "sourceProductId": js_string(data.get("sku")), "observedAt": meta["fetchedAt"],
                 "hash": meta["hash"], "offerCount": offer_count if finite(offer_count) else None, "availability": "listed-unconfirmed"}
    return {"part": part, "price": price}


def _clean_text(name) -> str:
    return _js_trim(LexborHTMLParser(f"<span>{name}</span>").css_first("span").text(deep=True))


def parse_search(html: str) -> list[dict]:
    tree = LexborHTMLParser(html)
    results: dict[str, dict] = {}

    def add(code, name):
        code = js_string(code) if code else ""
        if not js(r"^\d+$").search(code) or not name:
            return
        clean = _clean_text(name if isinstance(name, str) else js_string(name))
        if len(clean.encode("utf-16-le")) // 2 > 3 and code not in results:
            results[code] = {"pcode": code, "name": clean, "url": f"https://prod.danawa.com/info/?pcode={code}"}

    for el in tree.css('script[type="application/ld+json"]'):
        try:
            data = json.loads(el.text(deep=True))
            if not isinstance(data, dict):
                raise TypeError
            if data.get("@type") == "ItemList" or not data.get("@type"):
                for item in data.get("itemListElement") or []:
                    if item.get("url"):
                        add(_url(item["url"])[1].get("pcode"), item.get("name"))
        except (ValueError, TypeError, AttributeError):
            pass
    for el in tree.css("li[data-product-seq]"):
        code = el.attributes.get("data-product-seq")
        name = next((t for t in (_js_trim(a.text(deep=True)) for a in el.css('a[href*="pcode="]'))
                     if len(t) > 8 and "이미지" not in t and not js(r"^[\d,]+원$").search(t)), None)
        add(code, name)
    skip = js(r"이미지 보기|^[\d,]+원$|^의견|^상품평|가격비교 보기")
    for el in tree.css('a[href*="pcode="]'):
        name = _js_trim(el.text(deep=True))
        if len(name) < 8 or skip.search(name):
            continue
        try:
            host, params = _url(el.attributes.get("href") or "", "https://prod.danawa.com")
            if host == "prod.danawa.com":
                add(params.get("pcode"), name)
        except ValueError:
            pass
    # Public server-rendered product/bundle data, without calling restricted AJAX APIs.
    chunks = []
    push = js(r"self\.__next_f\.push\((\[[\s\S]*\])\)")
    for el in tree.css("script"):
        m = push.search(el.text(deep=True))
        if m:
            try:
                frame = json.loads(m.group(1))
                if frame and frame[0] == 1 and not isinstance(frame[0], bool) and len(frame) > 1 and isinstance(frame[1], str):
                    chunks.append(frame[1])
            except ValueError:
                pass
    for line in "".join(chunks).split("\n"):
        body = line[line.find(":") + 1:]
        if not body or body[0] not in "[{":
            continue
        try:
            value = json.loads(body)
        except ValueError:
            continue
        stack, nodes = [value], 0
        while stack and nodes < 200000:
            nodes += 1
            node = stack.pop()
            if not isinstance(node, (dict, list)):
                continue
            if isinstance(node, dict) and node.get("productUrl"):
                try:
                    host, params = _url(node["productUrl"])
                    if host == "prod.danawa.com":
                        name = node.get("name") or node.get("productName")
                        add(params.get("pcode"), name)
                        for bundle in node.get("bundleProducts") or []:
                            add(bundle.get("productCode"),
                                bundle.get("productName") or " / ".join(str(x) for x in (name, bundle.get("bundleName")) if x))
                except (ValueError, TypeError, AttributeError):
                    pass
            for child in js_values(node):
                if isinstance(child, (dict, list)):
                    stack.append(child)
    return list(results.values())


def _closest(node, classes: tuple[str, ...]) -> bool:
    while node is not None and node.tag != "-undef":
        cls = (node.attributes.get("class") or "").split() if node.tag else []
        if any(c in cls for c in classes):
            return True
        node = node.parent
    return False


def parse_popularity(html: str, category: str, source_url: str, observed_at: str) -> list[dict]:
    tree = LexborHTMLParser(html)
    if not any(_js_trim(el.text(deep=True)) == "인기상품순" for el in tree.css('[role="tab"][aria-selected="true"]')):
        return []
    found: dict[str, dict] = {}
    for item in tree.css(".dnw-product-list .dnw-catalog-item"):
        if _closest(item, ("dnw-ad-item", "dnw-ad-list-item")):
            continue
        marker = item.css_first('[aria-label^="인기순위 "]')
        m = js(r"^인기순위\s+(\d+)위$").search(marker.attributes.get("aria-label") or "") if marker else None
        rank = int(m.group(1)) if m else 0
        if rank < 1:
            continue
        rep = item.css_first('[data-testid="ProductListTitle"] a[href*="pcode="]')
        href = rep.attributes.get("href") if rep else None
        if href is None:
            continue
        try:
            family = _url(href)[1].get("pcode")
        except ValueError:
            continue
        for a in item.css('a[href*="pcode="]'):
            try:
                host, params = _url(a.attributes.get("href"))
            except ValueError:
                continue
            if host != "prod.danawa.com" or params.get("adinflow") == "Y":
                continue
            pcode = params.get("pcode")
            if not js(r"^\d+$").search(pcode or ""):
                continue
            found[pcode] = {"pcode": pcode, "popularity": {"rank": rank, "category": category, "sourceUrl": source_url,
                                                           "observedAt": observed_at, "sort": "BEST", "scope": "category-family",
                                                           "familyPcode": family}}
    return list(found.values())


def benchmark_name(category: str, name: str) -> str | None:
    if category == "cpu":
        amd = js(r"라이젠\s*([3579])(?:-\d+세대)?\s*(\d{4}[A-Z0-9]*)", "i").search(name)
        if amd:
            return f"AMD Ryzen {amd.group(1)} {amd.group(2).upper()}"
        intel = js(r"코어\s*(?:울트라\s*)?i?([3579])(?:-\d+세대|\s*시리즈\d+)?\s*\(?([1-9]\d{2,4}[A-Z]*)(?:\s*(Plus))?", "i").search(name)
        if intel:
            if _test("울트라", name):
                return f"Intel Core Ultra {intel.group(1)} {intel.group(2)}{' Plus' if intel.group(3) else ''}"
            return f"Intel Core i{intel.group(1)}-{intel.group(2)}"
    if category == "gpu":
        n = js(r"(?:RTX|GTX)\s*(\d{4})\s*(Ti)?\s*(SUPER)?", "i").search(name)
        if n:
            s = js(r"\s+").sub(" ", n.group(0))
            s = js(r"(RTX|GTX)\s*", "i").sub(lambda m: m.group(1) + " ", s, count=1)
            s = js(r"(\d)(Ti)", "i").sub(lambda m: m.group(1) + " " + m.group(2), s, count=1)
            return f"NVIDIA GeForce {_js_trim(s)}"
        a = js(r"RX\s*(\d{4})\s*(XTX|XT|GRE)?", "i").search(name)
        if a:
            return f"AMD Radeon RX {a.group(1)}{' ' + a.group(2).upper() if a.group(2) else ''}"
    return None


_EXCLUDED = r"중고|리퍼|렌탈|대여|완본체|조립PC|미니PC|노트북|서버용|ECC|SO-DIMM|SODIMM|등록 대행|해외구매|해외직구"
_DISCOVERY_REQUIRED = {"cpu": ("socket", "cores"), "board": ("socket", "ddr", "form", "slots"), "ram": ("ddr", "capacity"),
                       "gpu": ("vram", "length"), "ssd": ("capacity", "m2"), "psu": ("capacity", "connectors"),
                       "case": ("forms", "gpuLength", "coolerHeight"), "cooler": ("sockets", "height")}


def valid_discovered(part: dict) -> bool:
    if product_issues(part):
        return False
    if _test(_EXCLUDED, part.get("name") or "", "i"):
        return False
    if part.get("sourceCategory") == part.get("category") and (part.get("category") != "cooler" or _test(r"CPU.*쿨러", part.get("productType") or "", "i")):
        return True
    required = _DISCOVERY_REQUIRED.get(part.get("category"), ())
    return bool(required) and all(part.get(k) is not None for k in required)
