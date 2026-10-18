"""Per-user targets: estimated energy needs -> a calorie window for one smoothie, and the user's climate zone.

Energy: Mifflin-St Jeor BMR x activity factor = TDEE; weight management target = TDEE - 500 kcal (floored at
1200 kcal for women / 1500 kcal for men); a smoothie snack is 10-15 % of that day. The personal window is always
kept inside the research threshold for one smoothie, so personalisation can narrow a rule but never loosen it.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

ACTIVITY_FACTORS = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725}
ACTIVITY_LABELS = {"sedentary": "ít vận động", "light": "vận động nhẹ", "moderate": "vận động vừa", "active": "vận động nhiều"}
DEFAULT_ACTIVITY = "light"
DEFICIT_KCAL = 500
SNACK_SHARE = (0.10, 0.15)

# Province / city -> climate zone used by ingredient_seasons.region_scope.
_NORTH = ("ha noi", "hai phong", "quang ninh", "bac ninh", "bac giang", "hai duong", "hung yen", "thai binh", "nam dinh",
          "ninh binh", "ha nam", "vinh phuc", "phu tho", "thai nguyen", "tuyen quang", "ha giang", "cao bang", "bac kan",
          "lang son", "lao cai", "yen bai", "son la", "dien bien", "lai chau", "hoa binh", "mien bac")
_CENTRAL = ("thanh hoa", "nghe an", "ha tinh", "quang binh", "quang tri", "thua thien hue", "hue", "da nang", "quang nam",
            "quang ngai", "binh dinh", "phu yen", "khanh hoa", "ninh thuan", "binh thuan", "kon tum", "gia lai", "dak lak",
            "dak nong", "lam dong", "mien trung", "tay nguyen")
_SOUTH = ("ho chi minh", "hcm", "sai gon", "binh duong", "dong nai", "ba ria", "vung tau", "tay ninh", "binh phuoc",
          "long an", "tien giang", "ben tre", "tra vinh", "vinh long", "dong thap", "an giang", "kien giang", "can tho",
          "hau giang", "soc trang", "bac lieu", "ca mau", "mien nam", "mien tay")


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFD", value.lower().replace("đ", "d"))
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def region_scope(hometown: str | None) -> str | None:
    """'TP. Hồ Chí Minh' -> 'south'; unknown places -> None (season data is then used without a region filter)."""
    if not hometown:
        return None
    place = f" {_plain(hometown)} "
    for scope, names in (("north", _NORTH), ("central", _CENTRAL), ("south", _SOUTH)):
        if any(f" {name} " in place for name in names):
            return scope
    return None


def months_for(item: dict[str, Any], scope: str | None) -> list[int]:
    """Season months for the user's zone when the sheet has them, else every month the ingredient is in season."""
    by_scope = item.get("season_by_scope") or {}
    if scope and by_scope.get(scope):
        return list(by_scope[scope])
    return list(item.get("season_months") or [])


def _is_female(gender: str) -> bool | None:
    plain = _plain(gender or "")
    if plain in {"nu", "female", "f", "woman", "phu nu"}:
        return True
    if plain in {"nam", "male", "m", "man"}:
        return False
    return None


def energy_plan(profile: dict[str, Any]) -> dict[str, Any] | None:
    try:
        age = float(profile.get("age") or 0)
        height = float(profile.get("height_cm") or profile.get("heightCm") or 0)
        weight = float(profile.get("weight_kg") or profile.get("weightKg") or 0)
    except (TypeError, ValueError):
        return None
    if not (age and height and weight):
        return None
    assumptions: list[str] = []
    female = _is_female(str(profile.get("gender") or ""))
    base = 10 * weight + 6.25 * height - 5 * age
    if female is None:
        bmr = base - 78  # midpoint of the male (+5) and female (-161) constants
        assumptions.append("Giới tính không xác định: dùng trung bình hệ số nam/nữ khi ước tính năng lượng.")
    else:
        bmr = base - 161 if female else base + 5
    activity = str(profile.get("activity_level") or "").strip().lower()
    if activity not in ACTIVITY_FACTORS:
        activity = DEFAULT_ACTIVITY
        assumptions.append("Chưa khai báo mức vận động: tạm tính theo mức vận động nhẹ.")
    tdee = bmr * ACTIVITY_FACTORS[activity]
    floor = 1200 if female else 1500
    daily = max(tdee - DEFICIT_KCAL, floor)
    low, high = round(daily * SNACK_SHARE[0]), round(daily * SNACK_SHARE[1])
    return {
        "bmr_kcal": round(bmr),
        "activity_level": activity,
        "activity_label": ACTIVITY_LABELS[activity],
        "tdee_kcal": round(tdee),
        "daily_target_kcal": round(daily),
        "smoothie_kcal_min": low,
        "smoothie_kcal_max": high,
        "method": "Mifflin-St Jeor; mục tiêu giảm cân = TDEE - 500 kcal; bữa phụ 10-15%",
        "assumptions": assumptions,
    }


def personal_thresholds(thresholds: list[dict[str, Any]], plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Narrow the absolute calorie rule to the user's window (never outside the research range)."""
    if not plan:
        return [dict(rule) for rule in thresholds]
    out: list[dict[str, Any]] = []
    for rule in thresholds:
        rule = dict(rule)
        if rule.get("nutrient") == "calories" and rule.get("basis", "absolute") == "absolute":
            low = plan["smoothie_kcal_min"] if rule.get("minimum") is None else max(rule["minimum"], plan["smoothie_kcal_min"])
            high = plan["smoothie_kcal_max"] if rule.get("maximum") is None else min(rule["maximum"], plan["smoothie_kcal_max"])
            if low <= high:
                rule.update({
                    "minimum": float(low), "maximum": float(high), "comparator": "between",
                    "label": "Năng lượng (mục tiêu cá nhân)",
                    "code": f"{rule['code']}+CA_NHAN" if rule.get("code") else "MUC_TIEU_CA_NHAN",
                })
        out.append(rule)
    return out


def describe(plan: dict[str, Any] | None) -> str:
    if not plan:
        return ""
    return (
        f"Nhu cầu ước tính khoảng {plan['daily_target_kcal']} kcal/ngày để giảm cân ({plan['activity_label']}), "
        f"nên mỗi ly nhắm {plan['smoothie_kcal_min']}–{plan['smoothie_kcal_max']} kcal."
    )
