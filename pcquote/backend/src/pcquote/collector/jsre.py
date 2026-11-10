"""JavaScript-compatible regular expressions and value conversions.

The collector parsers were ported from buildmate's JavaScript. To give identical
results on real pages, `\\d` is ASCII-only and `\\s` is JavaScript's whitespace set
(Python's differ for non-ASCII digits and for U+FEFF / U+001C–U+001F / U+0085).
"""

from __future__ import annotations

import math
import re

_WS = "\\t\\n\\v\\f\\r \\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000\\ufeff"
_CLASS = {"d": "0-9", "s": _WS}
_NEGATED = {"D": "0-9", "S": _WS}


def _translate(pattern: str) -> str:
    out, i, in_class = [], 0, False
    while i < len(pattern):
        c = pattern[i]
        if c == "\\" and i + 1 < len(pattern):
            n = pattern[i + 1]
            if n in _CLASS:
                out.append(_CLASS[n] if in_class else f"[{_CLASS[n]}]")
            elif n in _NEGATED and not in_class:
                out.append(f"[^{_NEGATED[n]}]")
            else:
                out.append(c + n)
            i += 2
            continue
        if c == "[" and not in_class:
            in_class = True
        elif c == "]" and in_class:
            in_class = False
        out.append(c)
        i += 1
    return "".join(out)


_cache: dict[tuple[str, int], re.Pattern] = {}


def js(pattern: str, flags: str = "") -> re.Pattern:
    """Compile a JavaScript regex body. flags: 'i' only (global handled by the caller)."""
    key = (pattern, "i" in flags)
    if key not in _cache:
        _cache[key] = re.compile(_translate(pattern), re.I if "i" in flags else 0)
    return _cache[key]


def num(value: float):
    """A JavaScript number as Python: integral values become int so JSON matches."""
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    return value


def js_number(value):
    """JavaScript Number(value) for JSON values; NaN for anything not numeric."""
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip(" \t\n\v\f\r             "
                           "    　﻿")
        if text == "":
            return 0
        try:
            if re.fullmatch(r"0[xX][0-9a-fA-F]+", text):
                return int(text, 16)
            if re.fullmatch(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?|[+-]?Infinity", text):
                return num(float(text))
        except ValueError:
            pass
        return math.nan
    return math.nan


def js_string(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return str(num(value)) if value.is_integer() else repr(value)
    return str(value)


def safe_integer(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and abs(value) <= 2 ** 53 - 1


def finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def js_values(obj):
    """Object.values order: array-index keys ascending, then other keys in insertion order."""
    if isinstance(obj, list):
        return list(obj)
    index = sorted((k for k in obj if re.fullmatch(r"0|[1-9][0-9]*", k) and int(k) < 2 ** 32 - 1), key=int)
    seen = set(index)
    return [obj[k] for k in index] + [v for k, v in obj.items() if k not in seen]
