"""Two-page A4 report: page 1 = the recipe (profile, scores, ingredients, steps), page 2 = the personal analysis."""
from __future__ import annotations

import hashlib
import logging
import math
import os
from pathlib import Path
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from app.schemas.report_schema import NutritionReportDocument, PdfArtifact
from app.services.report_enrichment import structured_steps

# Fresh Citrus tokens (frontend/src/app/globals.css)
BRAND = HexColor("#F97316")
ACTION = HexColor("#C2410C")
ORANGE_SOFT = HexColor("#FFF3E8")
PEACH = HexColor("#FDBA74")
CREAM = HexColor("#FFFDF5")
CARD = HexColor("#FFFFFF")
LINE = HexColor("#F1E7D8")
STRONG = HexColor("#3A220D")
INK = HexColor("#2B1A0A")
MUTED = HexColor("#6B5A45")
SUBTLE = HexColor("#9A8A76")
NEUTRAL_SOFT = HexColor("#F5F5F4")
GREEN = HexColor("#84CC16")
GREEN_TEXT = HexColor("#4D7C0F")
GREEN_SOFT = HexColor("#F3FCE7")
GREEN_LINE = HexColor("#D9F99D")
YELLOW = HexColor("#FACC15")
YELLOW_TEXT = HexColor("#A16207")
YELLOW_SOFT = HexColor("#FFF8D6")
YELLOW_LINE = HexColor("#FDE68A")
CORAL_STRONG = HexColor("#E11D48")
CORAL_SOFT = HexColor("#FFF0F3")
CORAL_LINE = HexColor("#FECDD3")
WHITE = HexColor("#FFFFFF")

PAGE_W, PAGE_H = A4
LEFT, RIGHT = 36.0, PAGE_W - 36.0
CONTENT_W = RIGHT - LEFT
BOTTOM = 62.0  # content stops above the disclaimer + footer


def _register_fonts() -> tuple[str, str]:
    # Every candidate must cover Vietnamese diacritics; Helvetica does not.
    candidates = []
    env_regular, env_bold = os.getenv("PDF_FONT_REGULAR"), os.getenv("PDF_FONT_BOLD")
    if env_regular and env_bold:
        candidates.append(("ReportBody", "ReportBody-Bold", Path(env_regular), Path(env_bold)))
    candidates += [
        ("Poppins", "Poppins-SemiBold", Path("C:/Windows/Fonts/Poppins-Regular.ttf"), Path("C:/Windows/Fonts/Poppins-SemiBold.ttf")),
        ("ArialVN", "ArialVN-Bold", Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
        ("NotoSans", "NotoSans-Bold", Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"), Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf")),
        ("DejaVuSans", "DejaVuSans-Bold", Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
    ]
    for regular_name, bold_name, regular_path, bold_path in candidates:
        if regular_path.exists() and bold_path.exists():
            pdfmetrics.registerFont(TTFont(regular_name, str(regular_path)))
            pdfmetrics.registerFont(TTFont(bold_name, str(bold_path)))
            return regular_name, bold_name
    logging.getLogger(__name__).warning("No Vietnamese-capable TTF found; PDF falls back to Helvetica.")
    return "Helvetica", "Helvetica-Bold"


BODY_FONT, BOLD_FONT = _register_fonts()

# ------------------------------------------------------------------ nutrient view-model (mirrors report-detail.ts)

NUTRIENTS: list[tuple[str, str, str, tuple[str, ...]]] = [
    ("calories", "Năng lượng", "kcal", ("năng lượng", "calories", "energy", "kcal")),
    ("carbohydrate", "Tinh bột (carb)", "g", ("carb", "tinh bột", "glucid")),
    ("protein", "Đạm", "g", ("protein", "đạm")),
    ("fat", "Chất béo", "g", ("chất béo", "fat", "lipid")),
    ("fiber", "Chất xơ", "g", ("xơ", "fiber")),
    ("sugar", "Đường tổng", "g", ("đường", "sugar")),
    ("sodium", "Natri", "mg", ("natri", "sodium")),
]
SLIGHT_MARGIN = 0.2  # up to 20 % above the range still counts as "slightly high"

STATUS_STYLE = {
    "in": ("Trong khoảng", GREEN_TEXT, GREEN),
    "slightly_high": ("Cao nhẹ", YELLOW_TEXT, YELLOW),
    "high": ("Vượt khoảng", CORAL_STRONG, CORAL_STRONG),
    "low": ("Thấp hơn khoảng", YELLOW_TEXT, YELLOW),
    "unknown": ("Chưa có khoảng", SUBTLE, SUBTLE),
}

SEASON_STYLE = {
    "in_season": ("Đang vào mùa", GREEN_SOFT, GREEN_TEXT),
    "year_round": ("Có quanh năm", GREEN_SOFT, GREEN_TEXT),
    "out_of_season": ("Trái vụ", YELLOW_SOFT, YELLOW_TEXT),
    "not_seasonal": ("Không theo mùa", NEUTRAL_SOFT, MUTED),
    "unknown": ("Chưa có lịch mùa", NEUTRAL_SOFT, MUTED),
}


def nutrient_key(label: str) -> str | None:
    lower = label.lower()
    for key, _label, _unit, aliases in NUTRIENTS:
        if lower == key or any(alias in lower for alias in aliases):
            return key
    return None


def range_status(value: float | None, minimum: float | None, maximum: float | None) -> str:
    if value is None or (minimum is None and maximum is None):
        return "unknown"
    if maximum is not None and value > maximum:
        return "slightly_high" if value <= maximum * (1 + SLIGHT_MARGIN) else "high"
    if minimum is not None and value < minimum:
        return "low"
    return "in"


def nutrient_rows(doc: NutritionReportDocument) -> list[dict[str, Any]]:
    """One row per nutrient: the personal / energy-share range wins, the research threshold fills the rest."""
    thresholds: dict[str, Any] = {}
    for rule in doc.thresholds:
        key = nutrient_key(rule.nutrient)
        if key and rule.unit != "%" and key not in thresholds:  # % of energy cannot sit on a gram axis
            thresholds[key] = rule
    ranges = {key: item for item in doc.reference_ranges if (key := nutrient_key(item.nutrient))}
    rows = []
    for key, label, unit, _aliases in NUTRIENTS:
        value = getattr(doc.totals, key)
        value = None if value is None else round(float(value), 1)
        reference, rule = ranges.get(key), thresholds.get(key)
        minimum = reference.minimum if reference and reference.minimum is not None else (rule.minimum if rule else None)
        maximum = reference.maximum if reference and reference.maximum is not None else (rule.maximum if rule else None)
        basis = reference.basis if reference else ("Mức khuyến nghị cho bữa phụ" if rule else None)
        rows.append({"key": key, "label": label, "unit": unit, "value": value, "min": minimum, "max": maximum,
                     "basis": basis, "status": range_status(value, minimum, maximum)})
    return rows


# ------------------------------------------------------------------ drawing helpers

def _fmt(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "—"
    text = f"{value:.{digits}f}".rstrip("0").rstrip(".") if digits else f"{value:.0f}"
    return text.replace(".", ",")


def _short(value: Any, maximum: int) -> str:
    text = "—" if value in (None, "") else str(value)
    return text if len(text) <= maximum else text[: maximum - 1].rstrip() + "…"


def _fit(text: str, font: str, size: float, width: float) -> str:
    if pdfmetrics.stringWidth(text, font, size) <= width:
        return text
    while text and pdfmetrics.stringWidth(text + "…", font, size) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def _wrap(text: str, font: str, size: float, width: float, max_lines: int = 3) -> list[str]:
    words = str(text).split()
    lines: list[str] = []
    current = ""
    for index, word in enumerate(words):
        trial = f"{current} {word}".strip()
        if pdfmetrics.stringWidth(trial, font, size) <= width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) == max_lines:
            lines[-1] = _fit(lines[-1] + " " + " ".join(words[index:]), font, size, width)
            return lines
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + [_fit(" ".join(lines[max_lines - 1:]), font, size, width)]
    return lines


def _text(c: Canvas, text: str, x: float, y: float, width: float, *, font: str = BODY_FONT, size: float = 8,
          color=INK, leading: float | None = None, max_lines: int = 3) -> float:
    """Draws wrapped text from baseline y; returns the baseline after the last line."""
    leading = leading or size * 1.35
    c.setFont(font, size)
    c.setFillColor(color)
    for line in _wrap(text, font, size, width, max_lines):
        c.drawString(x, y, line)
        y -= leading
    return y


def _pill(c: Canvas, x: float, y: float, text: str, fill, color, *, size: float = 6.8, height: float = 13,
          stroke=None, right: bool = False) -> float:
    """Rounded badge whose bottom-left (or bottom-right when right=True) sits at x, y. Returns its width."""
    width = pdfmetrics.stringWidth(text, BOLD_FONT, size) + 12
    if right:
        x -= width
    c.setFillColor(fill)
    c.setStrokeColor(stroke or fill)
    c.roundRect(x, y, width, height, height / 2, fill=1, stroke=1 if stroke else 0)
    c.setFillColor(color)
    c.setFont(BOLD_FONT, size)
    c.drawString(x + 6, y + (height - size) / 2 + 1.2, text)
    return width


def _card(c: Canvas, x: float, top: float, width: float, height: float, *, fill=CARD, stroke=LINE, radius: float = 10) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.8)
    c.roundRect(x, top - height, width, height, radius, fill=1, stroke=1)


def _section(c: Canvas, title: str, y: float, note: str | None = None) -> float:
    c.setFillColor(STRONG)
    c.setFont(BOLD_FONT, 10.5)
    c.drawString(LEFT, y, title)
    if note:
        c.setFont(BODY_FONT, 7.5)
        c.setFillColor(MUTED)
        c.drawRightString(RIGHT, y, note)
    return y - 14


def _header(c: Canvas, doc: NutritionReportDocument, page: int) -> None:
    c.setFillColor(CREAM)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(BRAND)
    c.roundRect(LEFT, PAGE_H - 62, 26, 26, 8, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(BOLD_FONT, 14)
    c.drawCentredString(LEFT + 13, PAGE_H - 54, "C")
    c.setFillColor(STRONG)
    c.setFont(BOLD_FONT, 8.5)
    c.drawString(LEFT + 34, PAGE_H - 46, "FRESH CITRUS AI WELLNESS")
    c.setFont(BODY_FONT, 7)
    c.setFillColor(MUTED)
    c.drawString(LEFT + 34, PAGE_H - 57, "Báo cáo sinh tố cá nhân hóa")
    c.drawRightString(RIGHT, PAGE_H - 46, f"Ngày tạo: {doc.created_at.strftime('%d/%m/%Y %H:%M')} UTC")
    c.drawRightString(RIGHT, PAGE_H - 57, f"Mã report: {doc.report_id}")


def _footer(c: Canvas, doc: NutritionReportDocument, page: int) -> None:
    c.setFont(BOLD_FONT, 6.5)
    c.setFillColor(ACTION)
    c.drawString(LEFT, 47, _short(doc.quality_label, 130))
    c.setFont(BODY_FONT, 6.5)
    c.setFillColor(MUTED)
    c.drawString(LEFT, 38, _short(doc.disclaimer, 140))
    c.setStrokeColor(LINE)
    c.setLineWidth(0.8)
    c.line(LEFT, 30, RIGHT, 30)
    c.setFont(BODY_FONT, 6.8)
    c.setFillColor(SUBTLE)
    c.drawString(LEFT, 19, "Fresh Citrus AI Wellness • Báo cáo dinh dưỡng có thể truy xuất nguồn")
    c.drawRightString(RIGHT, 19, f"Trang {page}/2")


# ------------------------------------------------------------------ step icons (24-unit grid, like the web icons)

def _step_icon(c: Canvas, kind: str, x: float, y: float, size: float = 14) -> None:
    """Line icon inside a size x size box whose bottom-left is x, y."""
    s = size / 24.0

    def P(px: float, py: float) -> tuple[float, float]:  # SVG coords (y down) -> PDF
        return x + px * s, y + (24 - py) * s

    c.saveState()
    c.setStrokeColor(ACTION)
    c.setLineWidth(1.3)
    c.setLineCap(1)
    c.setLineJoin(1)
    path = c.beginPath()

    def poly(*points: tuple[float, float], close: bool = False) -> None:
        path.moveTo(*P(*points[0]))
        for point in points[1:]:
            path.lineTo(*P(*point))
        if close:
            path.close()

    def circle(cx: float, cy: float, r: float) -> None:
        px, py = P(cx, cy)
        path.circle(px, py, r * s)

    if kind == "wash":  # droplet
        path.moveTo(*P(12, 3))
        path.curveTo(*P(8, 8), *P(5, 11), *P(5, 15))
        path.curveTo(*P(5, 19), *P(8, 22), *P(12, 22))
        path.curveTo(*P(16, 22), *P(19, 19), *P(19, 15))
        path.curveTo(*P(19, 11), *P(16, 8), *P(12, 3))
    elif kind in ("peel", "cut"):  # knife
        poly((4, 20), (15, 9))
        poly((14, 4), (20, 10), (16, 14), (10, 8), close=True)
    elif kind == "soak":  # waves
        for wy in (10, 16):
            path.moveTo(*P(3, wy))
            path.curveTo(*P(6, wy - 3), *P(9, wy - 3), *P(12, wy))
            path.curveTo(*P(15, wy + 3), *P(18, wy + 3), *P(21, wy))
    elif kind == "weigh":  # scale
        poly((12, 3), (12, 21))
        poly((5, 7), (19, 7))
        poly((8, 21), (16, 21))
        poly((5, 7), (2, 14), (8, 14), (5, 7))
        poly((19, 7), (16, 14), (22, 14), (19, 7))
    elif kind == "add":  # plus in square
        poly((4, 4), (20, 4), (20, 20), (4, 20), close=True)
        poly((12, 8), (12, 16))
        poly((8, 12), (16, 12))
    elif kind == "blend":  # blender jar
        poly((7, 3), (17, 3), (15.5, 14), (8.5, 14), close=True)
        poly((8, 14), (16, 14), (17, 21), (7, 21), close=True)
    elif kind == "rest":  # clock
        circle(12, 12, 9)
        poly((12, 7), (12, 12), (15.5, 14))
    elif kind == "pour":  # glass
        poly((6, 8), (18, 8), (16.5, 21), (7.5, 21), close=True)
        poly((10, 8), (11, 3), (15, 3))
    else:  # check
        poly((5, 12.5), (10, 17.5), (19, 7))
    c.drawPath(path, stroke=1, fill=0)
    c.restoreState()


# ------------------------------------------------------------------ page 1: recipe

def _meta_line(doc: NutritionReportDocument) -> str:
    parts = []
    if doc.serving_ml:
        parts.append(f"≈ {doc.serving_ml} ml/ly")
    parts.append(f"{doc.servings} khẩu phần")
    if doc.meal_context:
        parts.append(doc.meal_context)
    parts.append(f"Mục tiêu: {doc.goal}")
    return " · ".join(parts)


def _profile_chips(c: Canvas, doc: NutritionReportDocument, y: float) -> float:
    profile = doc.profile_snapshot
    if not profile:
        return y
    chips: list[tuple[str, Any, Any]] = []
    if profile.gender:
        chips.append((f"{profile.gender}, {profile.age} tuổi" if profile.age else profile.gender, NEUTRAL_SOFT, STRONG))
    if profile.bmi:
        category = f" · {profile.bmi_category}" if profile.bmi_category else ""
        chips.append((f"BMI {_fmt(profile.bmi)}{category}", NEUTRAL_SOFT, STRONG))
    if profile.allergies:
        chips.append(("Dị ứng: " + ", ".join(profile.allergies[:4]), CORAL_SOFT, CORAL_STRONG))
    else:
        chips.append(("Không khai báo dị ứng", NEUTRAL_SOFT, MUTED))
    if profile.preferences:
        chips.append(("Thích: " + ", ".join(profile.preferences[:3]), ORANGE_SOFT, ACTION))
    if profile.dislikes:
        chips.append(("Không thích: " + ", ".join(profile.dislikes[:3]), NEUTRAL_SOFT, MUTED))
    c.setFont(BODY_FONT, 7)
    c.setFillColor(MUTED)
    c.drawString(LEFT, y + 3.5, "Hồ sơ đầu vào")
    x = LEFT + 56
    for text, fill, color in chips:
        text = _fit(text, BOLD_FONT, 6.8, RIGHT - LEFT - 70)
        width = pdfmetrics.stringWidth(text, BOLD_FONT, 6.8) + 12
        if x + width > RIGHT:
            x, y = LEFT + 56, y - 17
        x += _pill(c, x, y, text, fill, color) + 5
    return y - 22


def _score_tiles(c: Canvas, doc: NutritionReportDocument, top: float) -> float:
    scores, allergen = doc.scores, doc.allergen_check
    if not scores and not allergen:
        return top
    gap, height = 8.0, 80.0
    width = (CONTENT_W - 2 * gap) / 3
    tiles = []

    fit = scores.personal_fit if scores else None
    fit_lines = [f"{row.points:+d}  {row.label}" for row in fit.breakdown[:3]] if fit and fit.breakdown else (
        ["Đạt mọi ngưỡng đã kiểm tra"] if fit else ["Chưa đủ dữ liệu"])
    tiles.append(("Điểm phù hợp cá nhân", str(fit.value) if fit else "—", "/100" if fit else "", ACTION, fit_lines))

    seasonal = scores.seasonal if scores else None
    month = (scores.season_month if scores else None) or doc.created_at.month
    seasonal_note = [f"Theo khối lượng nguyên liệu tươi, tháng {month}"] if seasonal is not None else ["Chưa có lịch mùa cho nguyên liệu đã chọn"]
    tiles.append(("Điểm mùa vụ", str(seasonal) if seasonal is not None else "—", "/100" if seasonal is not None else "", GREEN_TEXT, seasonal_note))

    conflicts = allergen.conflicts if allergen else []
    if allergen and allergen.checked:
        allergen_note = [f"Đã đối chiếu: {', '.join(allergen.checked[:4])}"]
        allergen_note += [f"Xung đột: {', '.join(conflicts[:3])}"] if conflicts else [f"{allergen.checked_ingredients} nguyên liệu đã kiểm tra"]
    else:
        allergen_note = ["Hồ sơ chưa khai báo dị ứng"]
    tiles.append(("An toàn dị ứng", str(len(conflicts)), " xung đột", CORAL_STRONG if conflicts else GREEN_TEXT, allergen_note))

    for index, (title, value, suffix, color, notes) in enumerate(tiles):
        x = LEFT + index * (width + gap)
        _card(c, x, top, width, height, fill=CARD)
        c.setFont(BODY_FONT, 7.5)
        c.setFillColor(MUTED)
        c.drawString(x + 10, top - 15, title)
        c.setFont(BOLD_FONT, 22)
        c.setFillColor(color)
        c.drawString(x + 10, top - 40, value)
        c.setFont(BODY_FONT, 8)
        c.setFillColor(MUTED)
        c.drawString(x + 12 + pdfmetrics.stringWidth(value, BOLD_FONT, 22), top - 40, suffix)
        ny = top - 53
        for note in notes:
            ny = _text(c, note, x + 10, ny, width - 20, size=6.5, color=MUTED, leading=8.2, max_lines=1)
            if ny < top - height + 6:
                break
    return top - height - 16


def _ingredient_table(c: Canvas, doc: NutritionReportDocument, y: float) -> float:
    per_serving = doc.servings > 1
    y = _section(c, "Nguyên liệu & mùa vụ", y, "Định lượng cho cả mẻ" if per_serving else "Định lượng cho 1 ly")
    kcal_by = {row.ingredient_id: row.nutrition.calories for row in doc.ingredient_nutrition}
    kcal_by.update({row.name: row.nutrition.calories for row in doc.ingredient_nutrition})
    cols = {"name": LEFT + 8, "amount": LEFT + 250, "kcal": LEFT + 305, "season": LEFT + 322}
    c.setFillColor(ORANGE_SOFT)
    c.roundRect(LEFT, y - 6, CONTENT_W, 17, 6, fill=1, stroke=0)
    c.setFont(BOLD_FONT, 7)
    c.setFillColor(ACTION)
    c.drawString(cols["name"], y, "Nguyên liệu")
    c.drawRightString(cols["amount"], y, "Định lượng")
    c.drawRightString(cols["kcal"], y, "kcal/ly")
    c.drawString(cols["season"], y, "Mùa vụ & ghi chú")
    y -= 19
    for ingredient in doc.ingredients[:8]:
        kcal = kcal_by.get(ingredient.ingredient_id, kcal_by.get(ingredient.name))
        c.setFont(BOLD_FONT, 8)
        c.setFillColor(STRONG)
        c.drawString(cols["name"], y, _fit(ingredient.name, BOLD_FONT, 8, 175))
        c.setFont(BODY_FONT, 8)
        c.setFillColor(INK)
        c.drawRightString(cols["amount"], y, f"{_fmt(ingredient.amount)} {ingredient.unit}")
        c.drawRightString(cols["kcal"], y, _fmt(kcal, 0))
        status = ingredient.season.status if ingredient.season else "unknown"
        label, fill, color = SEASON_STYLE.get(status, SEASON_STYLE["unknown"])
        x = cols["season"] + _pill(c, cols["season"], y - 3.5, label, fill, color, size=6.4, height=12) + 4
        if ingredient.substitution_for:
            _pill(c, x, y - 3.5, f"Thay {ingredient.substitution_for}", ORANGE_SOFT, ACTION, size=6.4, height=12)
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        c.line(LEFT, y - 7, RIGHT, y - 7)
        y -= 17
    c.setFont(BOLD_FONT, 7.5)
    c.setFillColor(MUTED)
    c.drawString(cols["name"], y, "Tổng 1 ly")
    c.setFillColor(STRONG)
    c.drawRightString(cols["kcal"], y, _fmt(doc.totals.calories, 0))
    return y - 22


def _prep_steps(c: Canvas, doc: NutritionReportDocument, y: float) -> float:
    steps = doc.steps or [type("Step", (), step)() for step in structured_steps(doc.preparation_steps)]
    if not steps:
        return y
    note = f"Tổng khoảng {doc.prep_minutes} phút" if doc.prep_minutes else None
    y = _section(c, "Quá trình thực hiện", y, note) + 4
    columns, gap, height = 3, 8.0, 62.0
    width = (CONTENT_W - (columns - 1) * gap) / columns
    for index, step in enumerate(steps[:6]):
        row, col = divmod(index, columns)
        x, top = LEFT + col * (width + gap), y - row * (height + gap)
        _card(c, x, top, width, height, radius=8)
        c.setFillColor(ORANGE_SOFT)
        c.roundRect(x + 8, top - 30, 22, 22, 6, fill=1, stroke=0)
        _step_icon(c, step.kind, x + 12, top - 26)
        _pill(c, x + 4, top - 12, f"B{index + 1}", ACTION, WHITE, size=5.8, height=9)
        minutes = step.minutes
        timing = ("" if minutes is None else f" · {round(minutes * 60)} giây" if minutes < 1 else f" · {_fmt(minutes)} phút")
        c.setFont(BOLD_FONT, 7.8)
        c.setFillColor(STRONG)
        c.drawString(x + 36, top - 16, _fit(step.title, BOLD_FONT, 7.8, width - 44))
        if timing:
            c.setFont(BODY_FONT, 6.8)
            c.setFillColor(MUTED)
            c.drawString(x + 36, top - 26, timing.strip(" ·"))
        _text(c, step.detail, x + 8, top - 40, width - 16, size=6.6, color=MUTED, leading=8, max_lines=3)
    rows = math.ceil(min(len(steps), 6) / columns)
    return y - rows * (height + gap) - 10


def _usage_and_safety(c: Canvas, doc: NutritionReportDocument, y: float) -> None:
    y = _section(c, "Cách dùng & lưu ý an toàn", y)
    y = _text(c, doc.usage, LEFT, y, CONTENT_W, size=7.6, leading=10, max_lines=2)
    if doc.substitutions:
        y = _text(c, doc.substitutions, LEFT, y, CONTENT_W, size=7.2, color=MUTED, leading=9.5, max_lines=2)
    warning = doc.warning or "Không phát hiện xung đột dị ứng trong dữ liệu đã cung cấp."
    review = doc.decision != "pass"
    fill, stroke, color = (YELLOW_SOFT, YELLOW_LINE, YELLOW_TEXT) if review else (GREEN_SOFT, GREEN_LINE, GREEN_TEXT)
    room = y - 6 - BOTTOM
    lines = _wrap(warning, BODY_FONT, 7, CONTENT_W - 24, max(1, int((room - 26) // 9)))
    height = min(room, 26 + len(lines) * 9)
    if height < 30:
        return
    top = y - 4
    _card(c, LEFT, top, CONTENT_W, height, fill=fill, stroke=stroke, radius=8)
    c.setFont(BOLD_FONT, 8)
    c.setFillColor(color)
    c.drawString(LEFT + 12, top - 13, "Cần xem lại trước khi dùng" if review else "Lưu ý an toàn")
    c.setFont(BODY_FONT, 7)
    c.setFillColor(INK)
    ly = top - 24
    for line in lines:
        c.drawString(LEFT + 12, ly, line)
        ly -= 9


def _page_one(c: Canvas, doc: NutritionReportDocument) -> None:
    _header(c, doc, 1)
    y = PAGE_H - 96
    c.setFillColor(STRONG)
    c.setFont(BOLD_FONT, 20)
    for line in _wrap(doc.title, BOLD_FONT, 20, CONTENT_W, 2):
        c.drawString(LEFT, y, line)
        y -= 24
    y = _text(c, _meta_line(doc), LEFT, y + 4, CONTENT_W, size=8, color=MUTED, max_lines=1) - 10
    x = LEFT
    passed = doc.decision == "pass"
    x += _pill(c, x, y, "Đã đạt kiểm tra" if passed else "Cần xem xét", GREEN_SOFT if passed else YELLOW_SOFT,
               GREEN_TEXT if passed else YELLOW_TEXT) + 5
    month = (doc.scores.season_month if doc.scores else None) or doc.created_at.month
    if any(item.season and item.season.status == "in_season" for item in doc.ingredients):
        x += _pill(c, x, y, f"Đang vào mùa: Tháng {month}", GREEN_SOFT, GREEN_TEXT) + 5
    if doc.prep_minutes:
        _pill(c, x, y, f"Chuẩn bị ~{doc.prep_minutes} phút", ORANGE_SOFT, ACTION)
    y -= 22
    y = _profile_chips(c, doc, y)
    y = _score_tiles(c, doc, y)
    y = _ingredient_table(c, doc, y)
    y = _prep_steps(c, doc, y)
    _usage_and_safety(c, doc, y)
    _footer(c, doc, 1)


# ------------------------------------------------------------------ page 2: personal analysis

def _axis_max(row: dict[str, Any]) -> float:
    reference = row["max"] if row["max"] is not None else (row["min"] * 2 if row["min"] is not None else 0)
    return max(row["value"] or 0, reference, row["min"] or 0) * 1.25 or 1.0


def _range_bars(c: Canvas, rows: list[dict[str, Any]], x: float, top: float, width: float) -> float:
    c.setFont(BOLD_FONT, 9.5)
    c.setFillColor(STRONG)
    c.drawString(x, top, "Cân đối dinh dưỡng trên 1 ly")
    # legend
    lx = x + width
    c.setFont(BODY_FONT, 6.5)
    c.setFillColor(MUTED)
    lx -= pdfmetrics.stringWidth("Ly này", BODY_FONT, 6.5)
    c.drawString(lx, top, "Ly này")
    c.setFillColor(STRONG)
    c.circle(lx - 6, top + 2.3, 2.6, fill=1, stroke=0)
    lx -= 16 + pdfmetrics.stringWidth("Khoảng khuyến nghị", BODY_FONT, 6.5)
    c.setFillColor(MUTED)
    c.drawString(lx, top, "Khoảng khuyến nghị")
    c.setFillColor(GREEN_SOFT)
    c.setStrokeColor(GREEN_LINE)
    c.roundRect(lx - 18, top, 14, 5, 2.5, fill=1, stroke=1)

    y = top - 20
    label_w, value_w = 70.0, 78.0
    bar_x, bar_w = x + label_w, width - label_w - value_w - 8
    for row in rows:
        style_label, style_text, style_dot = STATUS_STYLE[row["status"]]
        c.setFont(BOLD_FONT, 7.6)
        c.setFillColor(STRONG)
        c.drawString(x, y, row["label"])
        end = _axis_max(row)
        c.setFillColor(NEUTRAL_SOFT)
        c.roundRect(bar_x, y - 1, bar_w, 7, 3.5, fill=1, stroke=0)
        if row["min"] is not None or row["max"] is not None:
            lo = (row["min"] or 0) / end * bar_w
            hi = (row["max"] if row["max"] is not None else end) / end * bar_w
            c.setFillColor(GREEN_SOFT)
            c.setStrokeColor(GREEN_LINE)
            c.setLineWidth(0.7)
            c.roundRect(bar_x + lo, y - 1, max(hi - lo, 2), 7, 3.5, fill=1, stroke=1)
        if row["value"] is not None:
            dot = min(row["value"] / end, 1) * bar_w
            c.setFillColor(WHITE)
            c.circle(bar_x + dot, y + 2.5, 4.6, fill=1, stroke=0)
            c.setFillColor(style_dot)
            c.circle(bar_x + dot, y + 2.5, 3.4, fill=1, stroke=0)
        if row["min"] is not None and row["max"] is not None:
            reference = f"{_fmt(row['min'])}–{_fmt(row['max'])} {row['unit']}"
        elif row["min"] is not None:
            reference = f"≥ {_fmt(row['min'])} {row['unit']}"
        elif row["max"] is not None:
            reference = f"≤ {_fmt(row['max'])} {row['unit']}"
        else:
            reference = "Chưa có khoảng tham chiếu"
        if row["basis"]:
            reference += f" · {row['basis']}"
        c.setFont(BODY_FONT, 6)
        c.setFillColor(SUBTLE)
        c.drawString(bar_x, y - 9, _fit(reference, BODY_FONT, 6, bar_w + 4))
        c.setFont(BOLD_FONT, 8)
        c.setFillColor(STRONG)
        c.drawRightString(x + width, y, "Chưa đủ dữ liệu" if row["value"] is None else f"{_fmt(row['value'])} {row['unit']}")
        if row["value"] is not None and row["status"] != "unknown":
            c.setFont(BOLD_FONT, 6.4)
            c.setFillColor(style_text)
            c.drawRightString(x + width, y - 9, style_label)
        c.setStrokeColor(LINE)
        c.setLineWidth(0.5)
        c.line(x, y - 14, x + width, y - 14)
        y -= 26
    return y


def _radar(c: Canvas, rows: list[dict[str, Any]], x: float, top: float, width: float) -> None:
    c.setFont(BOLD_FONT, 9.5)
    c.setFillColor(STRONG)
    c.drawString(x, top, "Cân bằng so với mức tham chiếu")
    axes = []
    for row in rows:
        reference = row["max"] if row["max"] is not None else row["min"]
        if row["value"] is not None and reference:
            axes.append((row["label"].split(" (")[0], min(row["value"] / reference, 1.5), row["status"]))
    if len(axes) < 3:
        _text(c, "Chưa đủ chất có khoảng tham chiếu để vẽ biểu đồ.", x, top - 18, width, size=7, color=MUTED)
        return
    radius = min(width / 2 - 34, 62)
    cx, cy = x + width / 2, top - 22 - radius - 14
    n = len(axes)

    def point(index: int, share: float) -> tuple[float, float]:
        angle = math.pi / 2 - 2 * math.pi * index / n
        r = radius * share / 1.5
        return cx + r * math.cos(angle), cy + r * math.sin(angle)

    c.setLineWidth(0.6)
    for ring in (0.5, 1.0, 1.5):
        c.setStrokeColor(PEACH if ring == 1.0 else LINE)
        c.setDash(2, 2) if ring == 1.0 else c.setDash()
        path = c.beginPath()
        for index in range(n):
            px, py = point(index, ring)
            path.moveTo(px, py) if index == 0 else path.lineTo(px, py)
        path.close()
        c.drawPath(path, stroke=1, fill=0)
    c.setDash()
    for index in range(n):
        c.setStrokeColor(LINE)
        c.line(cx, cy, *point(index, 1.5))
    path = c.beginPath()
    for index, (_label, share, _status) in enumerate(axes):
        px, py = point(index, share)
        path.moveTo(px, py) if index == 0 else path.lineTo(px, py)
    path.close()
    c.saveState()
    c.setFillColor(BRAND)
    c.setFillAlpha(0.18)
    c.setStrokeColor(BRAND)
    c.setLineWidth(1.4)
    c.drawPath(path, stroke=1, fill=1)
    c.restoreState()
    for index, (label, share, status) in enumerate(axes):
        px, py = point(index, share)
        c.setFillColor(STATUS_STYLE[status][2])
        c.circle(px, py, 2.4, fill=1, stroke=0)
        lx, ly = point(index, 1.5)
        dx = lx - cx
        c.setFont(BODY_FONT, 6.4)
        c.setFillColor(MUTED)
        text = f"{label} {round(share * 100)}%"
        if abs(dx) < 4:
            c.drawCentredString(lx, ly + (5 if ly > cy else -10), text)
        elif dx > 0:
            c.drawString(lx + 4, ly - 2, text)
        else:
            c.drawRightString(lx - 4, ly - 2, text)
    c.setFont(BODY_FONT, 6)
    c.setFillColor(SUBTLE)
    c.drawCentredString(cx, cy - radius - 22, "Vòng nét đứt = 100% mức tham chiếu (tối đa 150%)")


def _season_calendar(c: Canvas, doc: NutritionReportDocument, y: float) -> float:
    rows = [item for item in doc.ingredients if item.season and item.season.months]
    if not rows:
        return y
    month = (doc.scores.season_month if doc.scores else None) or doc.created_at.month
    y = _section(c, "Lịch mùa vụ nguyên liệu tươi", y, f"Tháng hiện tại: {month}")
    name_w = 112.0
    cell = (CONTENT_W - name_w) / 12
    current_x = LEFT + name_w + (month - 1) * cell
    height = 14 + len(rows) * 15
    c.setFillColor(ORANGE_SOFT)
    c.roundRect(current_x + 2, y - height + 8, cell - 4, height, 5, fill=1, stroke=0)
    c.setFont(BOLD_FONT, 6.6)
    for index in range(12):
        c.setFillColor(ACTION if index + 1 == month else SUBTLE)
        c.drawCentredString(LEFT + name_w + (index + 0.5) * cell, y, f"T{index + 1}")
    y -= 14
    for item in rows:
        c.setFont(BOLD_FONT, 7.4)
        c.setFillColor(STRONG)
        c.drawString(LEFT, y, _fit(item.name, BOLD_FONT, 7.4, name_w - 6))
        for index in range(12):
            px = LEFT + name_w + index * cell + (cell - 18) / 2
            if index + 1 in item.season.months:
                c.setFillColor(GREEN)
                c.roundRect(px, y - 1, 18, 8, 4, fill=1, stroke=0)
            else:
                c.setStrokeColor(SUBTLE)
                c.setLineWidth(0.5)
                c.setDash(1.5, 1.5)
                c.roundRect(px, y - 1, 18, 8, 4, fill=0, stroke=1)
                c.setDash()
        y -= 15
    c.setFont(BODY_FONT, 6.4)
    c.setFillColor(MUTED)
    c.setFillColor(GREEN)
    c.roundRect(LEFT, y - 1, 14, 6, 3, fill=1, stroke=0)
    c.setFillColor(MUTED)
    c.drawString(LEFT + 18, y, "Chính vụ")
    c.setStrokeColor(SUBTLE)
    c.setDash(1.5, 1.5)
    c.roundRect(LEFT + 60, y - 1, 14, 6, 3, fill=0, stroke=1)
    c.setDash()
    c.drawString(LEFT + 78, y, "Ngoài vụ (theo bảng mùa vụ; nguyên liệu không theo mùa không hiển thị)")
    return y - 20


def _threshold_checks(c: Canvas, doc: NutritionReportDocument, y: float) -> float:
    if not doc.thresholds:
        return y
    y = _section(c, "Đối chiếu với mức khuyến nghị", y)
    for rule in doc.thresholds[:6]:
        if y < BOTTOM + 70:
            break
        color = GREEN_TEXT if rule.status == "pass" else (YELLOW_TEXT if rule.status == "review" else SUBTLE)
        c.setFillColor(color)
        c.circle(LEFT + 3, y + 2.4, 2.6, fill=1, stroke=0)
        value = "Chưa đủ dữ liệu" if rule.value is None else f"{_fmt(rule.value)} {rule.unit}"
        c.setFont(BOLD_FONT, 7.4)
        c.setFillColor(STRONG)
        c.drawString(LEFT + 10, y, _fit(f"{rule.nutrient}: {value}", BOLD_FONT, 7.4, 200))
        c.setFont(BODY_FONT, 7)
        c.setFillColor(color)
        c.drawString(LEFT + 215, y, _fit(rule.message, BODY_FONT, 7, CONTENT_W - 215))
        y -= 12
    return y - 10


def _trust(c: Canvas, doc: NutritionReportDocument, y: float) -> None:
    if y < BOTTOM + 40:
        return
    y = _section(c, "Số liệu trong báo cáo đáng tin đến đâu?", y)
    coverage = round(doc.data_coverage * 100)
    c.setFont(BODY_FONT, 7.4)
    c.setFillColor(MUTED)
    c.drawString(LEFT, y, "Số liệu đã có")
    c.setFillColor(NEUTRAL_SOFT)
    c.roundRect(LEFT + 64, y, 180, 5, 2.5, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.roundRect(LEFT + 64, y, max(180 * doc.data_coverage, 5), 5, 2.5, fill=1, stroke=0)
    c.setFont(BOLD_FONT, 7.4)
    c.setFillColor(STRONG)
    c.drawString(LEFT + 250, y, f"{coverage}%")
    y -= 11
    if coverage >= 100:
        explain = "Mọi nguyên liệu đều có đủ số liệu dinh dưỡng, nên các con số ở trên được tính đầy đủ."
    else:
        explain = (f"Đã tìm được số liệu cho {coverage}% các chất cần tính của nguyên liệu. Phần còn thiếu chưa được "
                   "cộng vào tổng, nên con số thực tế có thể cao hơn một chút.")
    y = _text(c, explain, LEFT, y, CONTENT_W, size=7, color=MUTED, leading=9, max_lines=2) - 3
    blocks = [
        ("Số liệu nên kiểm tra lại", doc.data_checks, CORAL_STRONG),
        ("Còn thiếu", doc.missing_data, YELLOW_TEXT),
        ("Cách tính đã giả định", doc.assumptions, MUTED),
        ("Nguồn số liệu", doc.sources, MUTED),
    ]
    for title, items, color in blocks:
        if not items:
            continue
        if y < BOTTOM + 4:
            break
        c.setFont(BOLD_FONT, 7.2)
        c.setFillColor(color)
        c.drawString(LEFT, y, title + ":")
        offset = pdfmetrics.stringWidth(title + ": ", BOLD_FONT, 7.2)
        lines = max(1, min(3, int((y - BOTTOM) // 9)))
        y = _text(c, "; ".join(items), LEFT + offset, y, CONTENT_W - offset, size=7, color=INK, leading=9, max_lines=lines) - 3


def _page_two(c: Canvas, doc: NutritionReportDocument) -> None:
    _header(c, doc, 2)
    y = PAGE_H - 96
    c.setFont(BOLD_FONT, 18)
    c.setFillColor(STRONG)
    c.drawString(LEFT, y, "Phân tích cá nhân hóa")
    y = _text(c, doc.summary, LEFT, y - 17, CONTENT_W, size=7.8, color=MUTED, leading=10.4, max_lines=5) - 8
    rows = nutrient_rows(doc)
    split = 318.0
    _card(c, LEFT, y + 4, split, 214, radius=10)
    _card(c, LEFT + split + 10, y + 4, CONTENT_W - split - 10, 214, radius=10)
    _range_bars(c, rows, LEFT + 12, y - 12, split - 24)
    _radar(c, rows, LEFT + split + 22, y - 12, CONTENT_W - split - 34)
    y -= 230
    y = _season_calendar(c, doc, y)
    y = _threshold_checks(c, doc, y)
    _trust(c, doc, y)
    _footer(c, doc, 2)


def render_report_pdf(document: NutritionReportDocument, output_path: Path) -> PdfArtifact:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(output_path), pagesize=A4, pageCompression=1)
    canvas.setTitle(document.title)
    canvas.setAuthor("Fresh Citrus AI Wellness")
    canvas.setSubject(f"Báo cáo dinh dưỡng {document.report_id}")
    canvas.setKeywords("dinh dưỡng, sinh tố, Fresh Citrus, LangGraph")
    _page_one(canvas, document)
    canvas.showPage()
    _page_two(canvas, document)
    canvas.save()
    payload = output_path.read_bytes()
    return PdfArtifact(
        path=str(output_path.resolve()),
        page_count=2,
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
    )
