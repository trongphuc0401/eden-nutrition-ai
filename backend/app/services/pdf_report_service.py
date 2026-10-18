from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from app.schemas.report_schema import NutritionReportDocument, PdfArtifact


ORANGE = HexColor("#F97316")
ORANGE_DARK = HexColor("#C2410C")
CREAM = HexColor("#FFFDF5")
GREEN = HexColor("#16A34A")
YELLOW = HexColor("#FACC15")
INK = HexColor("#292524")
MUTED = HexColor("#78716C")
BORDER = HexColor("#FED7AA")
WHITE = HexColor("#FFFFFF")


def _register_fonts() -> tuple[str, str, str]:
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
    body = bold = "Helvetica"
    for regular_name, bold_name, regular_path, bold_path in candidates:
        if regular_path.exists() and bold_path.exists():
            pdfmetrics.registerFont(TTFont(regular_name, str(regular_path)))
            pdfmetrics.registerFont(TTFont(bold_name, str(bold_path)))
            body, bold = regular_name, bold_name
            break
    else:
        logging.getLogger(__name__).warning("No Vietnamese-capable TTF found; PDF falls back to Helvetica.")
    return body, bold, bold


BODY_FONT, BOLD_FONT, TITLE_FONT = _register_fonts()


def _short(value: Any, maximum: int) -> str:
    text = "—" if value in (None, "") else str(value)
    return text if len(text) <= maximum else text[: maximum - 1].rstrip() + "…"


def _wrap(text: str, font: str, size: float, width: float, max_lines: int = 3) -> list[str]:
    words = str(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if pdfmetrics.stringWidth(trial, font, size) <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) == max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    consumed = " ".join(lines)
    if len(consumed) < len(str(text)) and lines:
        lines[-1] = _short(lines[-1], max(4, len(lines[-1]) - 1))
    return lines


def _text(canvas: Canvas, text: str, x: float, y: float, width: float, *, font: str = BODY_FONT,
          size: float = 9, color=INK, leading: float = 12, max_lines: int = 3) -> float:
    canvas.setFont(font, size)
    canvas.setFillColor(color)
    for line in _wrap(text, font, size, width, max_lines):
        canvas.drawString(x, y, line)
        y -= leading
    return y


def _header(canvas: Canvas, document: NutritionReportDocument, page: int) -> None:
    width, height = A4
    canvas.setFillColor(CREAM)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFillColor(ORANGE)
    canvas.roundRect(34, height - 66, 30, 30, 8, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont(BOLD_FONT, 16)
    canvas.drawCentredString(49, height - 56, "C")
    canvas.setFillColor(INK)
    canvas.setFont(BOLD_FONT, 9)
    canvas.drawString(72, height - 45, "FRESH CITRUS AI WELLNESS")
    canvas.setFont(BODY_FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(72, height - 58, f"Mã report: {document.report_id}")
    canvas.drawRightString(width - 34, height - 45, document.created_at.strftime("%d/%m/%Y %H:%M UTC"))
    canvas.drawRightString(width - 34, height - 58, f"Trang {page}/2")


def _section(canvas: Canvas, title: str, y: float) -> float:
    canvas.setFillColor(ORANGE_DARK)
    canvas.setFont(BOLD_FONT, 10)
    canvas.drawString(36, y, title.upper())
    canvas.setStrokeColor(BORDER)
    canvas.line(36, y - 5, A4[0] - 36, y - 5)
    return y - 19


def _footer(canvas: Canvas, document: NutritionReportDocument, page: int) -> None:
    canvas.setStrokeColor(BORDER)
    canvas.line(36, 34, A4[0] - 36, 34)
    canvas.setFont(BODY_FONT, 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(36, 21, "Fresh Citrus AI Wellness • Báo cáo dinh dưỡng có thể truy xuất nguồn")
    canvas.drawRightString(A4[0] - 36, 21, f"{document.report_id} • {page}/2")


def _page_one(canvas: Canvas, doc: NutritionReportDocument) -> None:
    width, height = A4
    _header(canvas, doc, 1)
    y = height - 94
    canvas.setFillColor(INK)
    canvas.setFont(TITLE_FONT, 22)
    for line in _wrap(doc.title, TITLE_FONT, 22, width - 72, 2):
        canvas.drawString(36, y, line)
        y -= 27
    canvas.setFillColor(ORANGE_DARK)
    canvas.setFont(BOLD_FONT, 9)
    canvas.drawString(36, y, f"Mục tiêu: {_short(doc.goal, 90)}")
    canvas.drawRightString(width - 36, y, f"{doc.servings} khẩu phần")
    y -= 24
    y = _section(canvas, "Nguyên liệu và định lượng", y)
    canvas.setFillColor(ORANGE)
    canvas.roundRect(36, y - 17, width - 72, 20, 5, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont(BOLD_FONT, 8)
    canvas.drawString(44, y - 10, "NGUYÊN LIỆU")
    canvas.drawRightString(width - 44, y - 10, "ĐỊNH LƯỢNG")
    y -= 29
    for ingredient in doc.ingredients[:8]:
        canvas.setFillColor(INK)
        canvas.setFont(BODY_FONT, 8.5)
        canvas.drawString(44, y, _short(ingredient.name, 52))
        canvas.setFont(BOLD_FONT, 8.5)
        canvas.drawRightString(width - 44, y, f"{ingredient.amount:g} {ingredient.unit}")
        canvas.setStrokeColor(BORDER)
        canvas.line(44, y - 6, width - 44, y - 6)
        y -= 20
    y -= 3
    y = _section(canvas, "Cách chế biến", y)
    for index, step in enumerate(doc.preparation_steps[:6], 1):
        canvas.setFillColor(ORANGE)
        canvas.circle(45, y + 2, 7, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont(BOLD_FONT, 7)
        canvas.drawCentredString(45, y - 0.5, str(index))
        y = _text(canvas, step, 59, y + 5, width - 103, size=8, leading=11, max_lines=2) - 6
    y -= 14
    y = _section(canvas, "Cách sử dụng và thay thế", y)
    y = _text(canvas, doc.usage, 42, y, width - 84, size=8, leading=10, max_lines=3) - 3
    y = _text(canvas, doc.substitutions, 42, y, width - 84, size=8, color=MUTED, leading=10, max_lines=2) - 6
    warning = doc.warning or "Không phát hiện xung đột dị ứng trong dữ liệu đã cung cấp."
    warning_lines = _wrap(warning, BODY_FONT, 7.5, width - 92, 12)
    box_h = max(60, 40 + len(warning_lines) * 9)
    canvas.setFillColor(HexColor("#FFF7ED"))
    canvas.setStrokeColor(ORANGE)
    canvas.roundRect(36, max(48, y - box_h + 10), width - 72, box_h, 8, fill=1, stroke=1)
    canvas.setFillColor(ORANGE_DARK)
    canvas.setFont(BOLD_FONT, 9)
    canvas.drawString(46, max(48, y - box_h + 10) + box_h - 17, "LƯU Ý AN TOÀN")
    _text(canvas, warning, 46, max(48, y - box_h + 10) + box_h - 31,
          width - 92, size=7.5, leading=9, max_lines=12)
    _footer(canvas, doc, 1)


def _page_two(canvas: Canvas, doc: NutritionReportDocument) -> None:
    width, height = A4
    _header(canvas, doc, 2)
    y = height - 92
    canvas.setFont(TITLE_FONT, 20)
    canvas.setFillColor(INK)
    canvas.drawString(36, y, "Phân tích dinh dưỡng")
    y -= 22
    y = _text(canvas, doc.summary, 36, y, width - 72, size=8.5, leading=11, max_lines=3) - 5
    metrics = [
        ("CALORIES", doc.totals.calories, "kcal"), ("PROTEIN", doc.totals.protein, "g"),
        ("CARB", doc.totals.carbohydrate, "g"), ("CHẤT BÉO", doc.totals.fat, "g"),
        ("CHẤT XƠ", doc.totals.fiber, "g"), ("ĐƯỜNG", doc.totals.sugar, "g"),
    ]
    gap, card_w, card_h = 8, (width - 72 - 16) / 3, 47
    for index, (label, value, unit) in enumerate(metrics):
        row, col = divmod(index, 3)
        x, cy = 36 + col * (card_w + gap), y - row * (card_h + 7)
        canvas.setFillColor(WHITE)
        canvas.setStrokeColor(BORDER)
        canvas.roundRect(x, cy - card_h, card_w, card_h, 7, fill=1, stroke=1)
        canvas.setFillColor(MUTED)
        canvas.setFont(BOLD_FONT, 7)
        canvas.drawString(x + 9, cy - 14, label)
        canvas.setFillColor(ORANGE_DARK)
        canvas.setFont(BOLD_FONT, 14)
        display = "—" if value is None else f"{value:g}"
        canvas.drawString(x + 9, cy - 35, f"{display} {unit}")
    y -= 2 * (card_h + 7) + 5
    y = _section(canvas, "Đóng góp theo nguyên liệu (mỗi khẩu phần)", y)
    columns = [36, 235, 304, 374, 444, 516]
    headers = ["Nguyên liệu", "kcal", "Protein", "Carb", "Béo", "Xơ"]
    canvas.setFillColor(ORANGE)
    canvas.rect(36, y - 17, width - 72, 19, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont(BOLD_FONT, 7)
    for x, header in zip(columns, headers):
        canvas.drawString(x + (4 if x == 36 else 0), y - 10, header)
    y -= 27
    for item in doc.ingredient_nutrition[:8]:
        values = [item.name, item.nutrition.calories, item.nutrition.protein, item.nutrition.carbohydrate,
                  item.nutrition.fat, item.nutrition.fiber]
        canvas.setFillColor(INK)
        canvas.setFont(BODY_FONT, 7)
        for index, (x, value) in enumerate(zip(columns, values)):
            canvas.drawString(x + (4 if index == 0 else 0), y, _short(value if index == 0 else ("—" if value is None else f"{value:g}"), 27 if index == 0 else 8))
        canvas.setStrokeColor(BORDER)
        canvas.line(36, y - 5, width - 36, y - 5)
        y -= 16
    y -= 2
    y = _section(canvas, "Ngưỡng đánh giá", y)
    for rule in doc.thresholds[:5]:
        color = GREEN if rule.status == "pass" else ORANGE_DARK
        canvas.setFillColor(color)
        canvas.circle(41, y + 2, 3, fill=1, stroke=0)
        canvas.setFillColor(INK)
        canvas.setFont(BOLD_FONT, 7.5)
        value = "—" if rule.value is None else f"{rule.value:g} {rule.unit}"
        canvas.drawString(49, y, f"{rule.nutrient}: {value}")
        canvas.setFont(BODY_FONT, 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(205, y, _short(rule.message, 66))
        y -= 13
    y -= 2
    y = _section(canvas, "Độ phủ, giả định và nguồn", y)
    canvas.setFont(BOLD_FONT, 8)
    canvas.setFillColor(INK)
    canvas.drawString(42, y, f"Độ phủ dữ liệu: {doc.data_coverage * 100:.0f}%")
    y -= 13
    detail = "; ".join((doc.missing_data or ["Không có dữ liệu thiếu đã ghi nhận"])[:2])
    y = _text(canvas, "Dữ liệu thiếu: " + detail, 42, y, width - 84, size=7, leading=9, max_lines=2)
    assumption = "; ".join((doc.assumptions or ["Không có giả định bổ sung"])[:2])
    y = _text(canvas, "Giả định: " + assumption, 42, y - 2, width - 84, size=7, leading=9, max_lines=2)
    sources = "; ".join(doc.sources[:6]) or "Chưa có nguồn dữ liệu"
    y = _text(canvas, "Nguồn: " + sources, 42, y - 2, width - 84, size=6.7, color=MUTED, leading=8, max_lines=3)
    canvas.setFont(BOLD_FONT, 6.5)
    canvas.setFillColor(ORANGE_DARK)
    canvas.drawString(36, 52, _short(doc.quality_label, 125))
    canvas.setFont(BODY_FONT, 6.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(36, 43, _short(doc.disclaimer, 125))
    _footer(canvas, doc, 2)


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
