"""Cell-level cleaning helpers. Every function is pure and returns data plus what it had to fix."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Any

_MISSING = {"", "-", "--", "—", "n/a", "na", "null", "none", "example_only", "needs_source"}
_TRUTHY = {"true", "1", "yes", "y", "có", "co"}
_FALSY = {"false", "0", "no", "n", "không", "khong"}


def strip_accents(value: str) -> str:
    value = value.replace("Đ", "D").replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn")


def normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", strip_accents(value).lower()).strip()


def text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    cleaned = re.sub(r"[ \t]+", " ", str(value)).strip()
    return cleaned or None


def is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip().lower() in _MISSING)


def to_bool(value: Any, default: bool | None = None) -> bool | None:
    if isinstance(value, bool):
        return value
    cleaned = str(value).strip().lower() if value is not None else ""
    if cleaned in _TRUTHY:
        return True
    if cleaned in _FALSY:
        return False
    return default


def to_number(value: Any) -> tuple[float | None, str, str | None]:
    """Return (number, status, note). status: measured | not_available | repaired | invalid.

    Excel turns typed decimals like "8.3" into dates (8 March) in d.m locales; the cell then
    arrives here as a datetime. We rebuild it as day.month and mark it `repaired` so it is
    reviewed - values such as "8.03" are unrecoverable and will still look like 8.3.
    """
    if is_missing(value):
        return None, "not_available", None
    if isinstance(value, (datetime, date)):
        return float(f"{value.day}.{value.month}"), "repaired", f"date {value:%Y-%m-%d} read as {value.day}.{value.month}"
    if isinstance(value, bool):
        return None, "invalid", f"boolean {value!r} in numeric cell"
    if isinstance(value, (int, float)):
        return float(value), "measured", None
    cleaned = str(value).strip().replace(",", ".")
    match = re.fullmatch(r"[<>≤≥~]?\s*(-?\d+(?:\.\d+)?)", cleaned)
    if match:
        return float(match.group(1)), "measured", None
    if cleaned.lower() in {"tr", "trace", "vết"}:
        return 0.0, "measured", "trace amount stored as 0"
    return None, "invalid", f"not a number: {cleaned[:40]!r}"


def to_int(value: Any) -> int | None:
    number, status, _ = to_number(value)
    return int(number) if number is not None and status in ("measured",) else None


# ------------------------------------------------------------------ sources
def source_code(raw: str) -> str:
    """'SRC_2892 QĐ/BYT' -> 'SRC_2892_QD_BYT' (must match ^[A-Z0-9_]+$, max 80)."""
    code = re.sub(r"[^A-Z0-9]+", "_", strip_accents(raw).upper()).strip("_")
    return code[:80]


def split_source_refs(cell: Any, known: set[str]) -> tuple[list[str], list[str]]:
    """Split a source cell into registered codes. Returns (codes, unknown_raw).

    Codes themselves may contain spaces, so we split only on newlines/;/, and then resolve each
    part against the register (exact, then prefix) rather than splitting on whitespace.
    """
    found: list[str] = []
    unknown: list[str] = []
    for part in re.split(r"[\n;]+|,\s*(?=SRC_|SCR_|NIH_|FDA_)", str(cell or "")):
        part = part.strip()
        if is_missing(part) or part.lower().startswith("http"):
            continue
        code = source_code(part)
        if code in known:
            found.append(code)
            continue
        prefix = [k for k in known if k.startswith(code) or code.startswith(k)]
        if len(prefix) == 1:
            found.append(prefix[0])
        else:
            unknown.append(part)
    return list(dict.fromkeys(found)), unknown


# ------------------------------------------------------------------ seasons
_YEAR_ROUND = r"qu[a-zà-ỹ]*\s*n[aă]m"
_SEASON_RE = re.compile(rf"({_YEAR_ROUND}|[\d][\d,\s\-]*)\s*\(([^)]*)\)", re.IGNORECASE)


def _months(fragment: str) -> list[int]:
    months: list[int] = []
    for part in re.split(r"[,\s]+", fragment.strip()):
        if not part:
            continue
        if "-" in part:
            lo, _, hi = part.partition("-")
            if lo.isdigit() and hi.isdigit():
                lo_i, hi_i = int(lo), int(hi)
                months += list(range(lo_i, hi_i + 1)) if lo_i <= hi_i else list(range(lo_i, 13)) + list(range(1, hi_i + 1))
        elif part.isdigit():
            months.append(int(part))
    return sorted({m for m in months if 1 <= m <= 12})


def _scope(label: str) -> str:
    low = strip_accents(label).lower()
    if "mien bac" in low:
        return "north"
    if "mien trung" in low or "trung bo" in low:
        return "central"
    if "mien nam" in low:
        return "south"
    return "province"


def parse_seasons(raw: Any) -> list[dict[str, Any]]:
    """'1,2,3 (Hòa Bình);10,11,12 (Miền Bắc); quanh năm (Miền Nam)' -> structured rows."""
    cell = text(raw)
    if not cell or is_missing(cell):
        return []
    rows = []
    for months_part, label in _SEASON_RE.findall(cell):
        year_round = not months_part.strip()[:1].isdigit()
        label = label.strip()
        rows.append({
            "region_label": label, "region_scope": _scope(label),
            "months": [] if year_round else _months(months_part), "year_round": year_round,
        })
    if not rows:  # bare list without regions: "1,2,3" or "quanh năm"
        if re.fullmatch(_YEAR_ROUND, cell, re.IGNORECASE):
            rows.append({"region_label": "Cả nước", "region_scope": "all", "months": [], "year_round": True})
        elif re.fullmatch(r"\d{1,2}(\.\d{1,2})+", cell):  # "5.6" = months 5,6 mangled into a decimal
            rows.append({"region_label": "Cả nước", "region_scope": "all", "months": _months(cell.replace(".", ",")), "year_round": False})
        elif re.fullmatch(r"[\d,\s\-]+", cell):
            rows.append({"region_label": "Cả nước", "region_scope": "all", "months": _months(cell), "year_round": False})
    return [r for r in rows if r["months"] or r["year_round"]]


def split_regions(raw: Any) -> list[str]:
    cell = text(raw)
    if not cell:
        return []
    return [p.strip() for p in re.split(r"[/,;]| và ", cell) if p.strip()]


# ------------------------------------------------------------------ thresholds / rules
def parse_threshold_text(raw: Any) -> tuple[float | None, str | None]:
    """'<0.5g/single smoothie ...' or '< 5,7/single smoothie mg' -> (0.5, 'g'), (5.7, 'mg')."""
    cell = text(raw)
    if not cell:
        return None, None
    number = re.search(r"(\d+(?:[.,]\d+)?)", cell)
    if not number:
        return None, None
    unit = re.search(r"\d\s*(mg|ug|µg|g|kcal|%)(?![a-z])", cell, re.IGNORECASE) or re.search(r"\b(mg|ug|g|kcal)\b", cell)
    return float(number.group(1).replace(",", ".")), (unit.group(1).lower() if unit else None)


def comparator_from_rule(rule: str | None, min_value: float | None, max_value: float | None) -> str:
    rule = (rule or "").lower()
    if min_value is not None and max_value is not None and ("and" in rule or "between" in rule or not rule):
        return "between"
    if "<=" in rule or ("<" not in rule and ">" not in rule and max_value is not None and min_value is None):
        return "lte"
    if ">=" in rule:
        return "gte"
    if "<" in rule:
        return "lt"
    if ">" in rule:
        return "gt"
    return "between" if min_value is not None and max_value is not None else ("gte" if min_value is not None else "lte")


def normalize_severity(value: Any) -> str | None:
    cleaned = (text(value) or "").lower()
    return cleaned if cleaned in {"low", "medium", "high", "critical"} else None


# ------------------------------------------------------------------ recipes
_ITEM_RE = re.compile(r"^(?P<name>.+?)\s*(?P<amount>\d+(?:[.,]\d+)?)\s*(?P<unit>g|ml)\s*$", re.IGNORECASE)


def parse_recipe_items(raw: Any) -> list[dict[str, Any]]:
    """'Bưởi 120g; sữa đậu nành không đường 200ml' -> items. ml is treated as 1 g/ml."""
    items = []
    for order, part in enumerate(p for p in re.split(r"[;\n]+", str(raw or "")) if p.strip()):
        match = _ITEM_RE.match(part.strip())
        if not match:
            items.append({"sort_order": order, "raw_text": part.strip(), "name": part.strip(), "amount": None, "unit": None})
            continue
        amount = float(match.group("amount").replace(",", "."))
        items.append({
            "sort_order": order, "raw_text": part.strip(), "name": match.group("name").strip(" ,-"),
            "amount": amount, "unit": match.group("unit").lower(),
        })
    return items


def parse_range(raw: Any) -> tuple[float | None, float | None]:
    """'25-35' -> (25, 35); '65' -> (65, 65)."""
    cell = text(raw)
    if not cell:
        return None, None
    numbers = re.findall(r"\d+(?:[.,]\d+)?", cell)
    if not numbers:
        return None, None
    values = [float(n.replace(",", ".")) for n in numbers]
    return values[0], values[-1]


def code_slug(raw: str) -> str:
    """'CRIT_ALLERGY_MACADAMIA NUT' -> 'CRIT_ALLERGY_MACADAMIA_NUT'."""
    return re.sub(r"[^A-Z0-9]+", "_", strip_accents(raw).upper()).strip("_")
