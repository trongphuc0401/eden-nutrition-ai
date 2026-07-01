from pathlib import Path
from textwrap import dedent

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as error:
    raise SystemExit("Pillow is required to build diagram images for this document.") from error


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "Docs"
ASSET_DIR = DOCS_DIR / "learning_doc_assets"
OUTPUT_PATH = DOCS_DIR / "AI_Backend_Learning_Guide.docx"

BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
INK = "0B2545"
LIGHT_BLUE = "E8EEF5"
LIGHT_GRAY = "F2F4F7"
GREEN = "DFF3E3"
YELLOW = "FFF4CC"
RED = "FCE4E4"
PURPLE = "EEE8FA"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_text(cell, text: str, bold: bool = False, color: str = "000000") -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.size = Pt(9.5)
    run.font.color.rgb = RGBColor.from_string(color)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def set_table_borders(table, color: str = "D9E2EC") -> None:
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "6")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_table_widths(table, widths: list[float]) -> None:
    for row in table.rows:
        for index, width in enumerate(widths):
            row.cells[index].width = Inches(width)


def configure_styles(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.18

    for style_name, size, color, before, after in [
        ("Heading 1", 16, BLUE, 18, 10),
        ("Heading 2", 13, BLUE, 14, 7),
        ("Heading 3", 12, DARK_BLUE, 10, 5),
    ]:
        style = doc.styles[style_name]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)


def add_title(doc: Document) -> None:
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Sổ Tay Học Backend và AI Engineer")
    run.bold = True
    run.font.size = Pt(25)
    run.font.color.rgb = RGBColor.from_string(INK)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(
        "Dành cho người mới bắt đầu, bám sát dự án AI Nutrition Coach"
    )
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor.from_string(DARK_BLUE)

    callout(
        doc,
        "Mục tiêu của tài liệu",
        "Sau khi đi hết tài liệu này, bạn không cần trở thành senior ngay. Điều quan trọng là bạn hiểu được dự án đang làm gì, vì sao mỗi phần tồn tại, cách đọc code backend/AI, và cách đưa ra quyết định phát triển tiếp một cách có nền tảng.",
        fill=GREEN,
    )


def callout(doc: Document, title: str, body: str, fill: str = LIGHT_BLUE) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_table_borders(table, "FFFFFF")
    cell = table.cell(0, 0)
    set_cell_shading(cell, fill)
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(3)
    run = paragraph.add_run(title)
    run.bold = True
    run.font.color.rgb = RGBColor.from_string(INK)
    run.font.size = Pt(11)
    paragraph = cell.add_paragraph(body)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.runs[0].font.size = Pt(10)


def add_tab_header(doc: Document, tab: str, title: str, purpose: str) -> None:
    doc.add_heading(f"{tab}. {title}", level=1)
    callout(doc, "Ban se hoc duoc gi", purpose, fill=LIGHT_BLUE)


def add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        paragraph = doc.add_paragraph(style="List Bullet")
        paragraph.add_run(item)


def add_steps(doc: Document, items: list[str]) -> None:
    for item in items:
        paragraph = doc.add_paragraph(style="List Number")
        paragraph.add_run(item)


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float]) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    set_table_borders(table)
    set_table_widths(table, widths)
    for index, header in enumerate(headers):
        set_cell_shading(table.rows[0].cells[index], LIGHT_BLUE)
        set_cell_text(table.rows[0].cells[index], header, bold=True, color=INK)
    for row_values in rows:
        row = table.add_row()
        for index, value in enumerate(row_values):
            set_cell_text(row.cells[index], value)
    doc.add_paragraph()


def get_font(size: int = 28, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def draw_wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], width: int, font, fill):
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + 8


def rounded_box(draw, xy, fill, outline, radius=22):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=3)


def arrow(draw, start, end, fill="#315E8A"):
    draw.line([start, end], fill=fill, width=5)
    x1, y1 = start
    x2, y2 = end
    if x2 >= x1:
        points = [(x2, y2), (x2 - 16, y2 - 10), (x2 - 16, y2 + 10)]
    else:
        points = [(x2, y2), (x2 + 16, y2 - 10), (x2 + 16, y2 + 10)]
    draw.polygon(points, fill=fill)


def make_system_map(path: Path) -> None:
    img = Image.new("RGB", (1600, 900), "white")
    draw = ImageDraw.Draw(img)
    title_font = get_font(42, True)
    box_font = get_font(25, True)
    small_font = get_font(20)
    draw.text((70, 40), "Bản đồ tổng quan AI Nutrition Coach", font=title_font, fill="#0B2545")
    boxes = [
        ((70, 170, 350, 330), "#E8EEF5", "Người dùng", "Nhập tuổi, cân nặng, dị ứng, sở thích"),
        ((430, 170, 710, 330), "#DFF3E3", "FastAPI", "Cửa vào backend: endpoint và response"),
        ((790, 170, 1070, 330), "#FFF4CC", "Services", "Xử lý BMI, RAG, guardrail, evaluation"),
        ((1150, 170, 1430, 330), "#EEE8FA", "AI Graph", "Tạo công thức smoothie có cấu trúc"),
        ((430, 520, 710, 710), "#F2F4F7", "Data", "Fruit seed, rules, DB, vector sau này"),
        ((790, 520, 1070, 710), "#FCE4E4", "Guardrail", "Chặn dị ứng, ngoài scope, cảnh báo y tế"),
        ((1150, 520, 1430, 710), "#DFF3E3", "Evaluation", "Score, pass/review/reject, khuyến nghị"),
    ]
    for box, color, heading, body in boxes:
        rounded_box(draw, box, color, "#B7C7D9")
        draw.text((box[0] + 24, box[1] + 24), heading, font=box_font, fill="#0B2545")
        draw_wrapped(draw, body, (box[0] + 24, box[1] + 72), box[2] - box[0] - 48, small_font, "#1F2937")
    for start, end in [
        ((350, 250), (430, 250)),
        ((710, 250), (790, 250)),
        ((1070, 250), (1150, 250)),
        ((570, 520), (570, 335)),
        ((930, 335), (930, 520)),
        ((1070, 615), (1150, 615)),
    ]:
        arrow(draw, start, end)
    draw.text((70, 820), "Ý tưởng lớn: backend là bộ não điều phối, AI là công cụ tạo kết quả, guardrail/evaluation là lớp an toàn.", font=small_font, fill="#334155")
    img.save(path)


def make_request_flow(path: Path) -> None:
    img = Image.new("RGB", (1600, 900), "white")
    draw = ImageDraw.Draw(img)
    title_font = get_font(42, True)
    step_font = get_font(23, True)
    body_font = get_font(19)
    draw.text((70, 40), "Một request đi qua backend như thế nào", font=title_font, fill="#0B2545")
    steps = [
        ("1. ProfileInput", "Pydantic kiểm tra dữ liệu đầu vào: age, BMI, allergy, goal."),
        ("2. Profile analysis", "Tính BMI và xác định overweight/obesity hay ngoài scope."),
        ("3. Knowledge", "Tìm kiến thức trái cây Việt Nam từ vector DB hoặc local seed."),
        ("4. Generate", "LangGraph/OpenAI tạo công thức smoothie có cấu trúc."),
        ("5. Guardrail", "Chặn thành phần dị ứng, disliked ingredient, cảnh báo medical notes."),
        ("6. Evaluate", "Tính dinh dưỡng, check threshold, safety rule, score và decision."),
    ]
    x_positions = [80, 570, 1060]
    y_positions = [170, 500]
    index = 0
    for y in y_positions:
        for x in x_positions:
            heading, body = steps[index]
            rounded_box(draw, (x, y, x + 390, y + 210), "#E8EEF5" if index % 2 == 0 else "#DFF3E3", "#B7C7D9")
            draw.text((x + 22, y + 20), heading, font=step_font, fill="#0B2545")
            draw_wrapped(draw, body, (x + 22, y + 68), 340, body_font, "#1F2937")
            index += 1
    for start, end in [
        ((470, 275), (570, 275)),
        ((960, 275), (1060, 275)),
        ((1255, 380), (1255, 500)),
        ((1060, 605), (960, 605)),
        ((570, 605), (470, 605)),
    ]:
        arrow(draw, start, end)
    img.save(path)


def make_ai_pipeline(path: Path) -> None:
    img = Image.new("RGB", (1600, 900), "white")
    draw = ImageDraw.Draw(img)
    title_font = get_font(42, True)
    label_font = get_font(24, True)
    body_font = get_font(19)
    draw.text((70, 40), "AI pipeline: RAG + Prompt + Structured Output", font=title_font, fill="#0B2545")
    items = [
        ((90, 190, 410, 370), "#F2F4F7", "RAG", "Lấy kiến thức liên quan từ data trước khi hỏi AI."),
        ((500, 190, 820, 370), "#E8EEF5", "Prompt", "Đặt vai trò, mục tiêu, ràng buộc và context cho AI."),
        ((910, 190, 1230, 370), "#DFF3E3", "Structured Output", "Bắt AI trả về đúng schema SmoothiePlanResponse."),
        ((500, 560, 820, 740), "#FFF4CC", "Fallback", "Không có API key vẫn có dry-run để dev và test."),
        ((910, 560, 1230, 740), "#FCE4E4", "Safety", "Kết quả AI không được tin 100%, phải check lại."),
    ]
    for box, color, label, body in items:
        rounded_box(draw, box, color, "#B7C7D9")
        draw.text((box[0] + 24, box[1] + 24), label, font=label_font, fill="#0B2545")
        draw_wrapped(draw, body, (box[0] + 24, box[1] + 76), box[2] - box[0] - 48, body_font, "#1F2937")
    for start, end in [
        ((410, 280), (500, 280)),
        ((820, 280), (910, 280)),
        ((1070, 370), (1070, 560)),
        ((820, 650), (910, 650)),
    ]:
        arrow(draw, start, end)
    draw.text((90, 805), "Cách nghĩ đúng: AI không thay backend. AI chỉ là một bước trong pipeline có kiểm soát.", font=body_font, fill="#334155")
    img.save(path)


def make_learning_roadmap(path: Path) -> None:
    img = Image.new("RGB", (1600, 900), "white")
    draw = ImageDraw.Draw(img)
    title_font = get_font(42, True)
    label_font = get_font(22, True)
    body_font = get_font(18)
    draw.text((70, 40), "Lộ trình học 30 ngày theo dự án này", font=title_font, fill="#0B2545")
    weeks = [
        ("Tuần 1", "Đọc được code Python cơ bản, schema, function, class."),
        ("Tuần 2", "Hiểu FastAPI: endpoint, request, response, status code."),
        ("Tuần 3", "Hiểu AI pipeline: prompt, RAG, structured output, fallback."),
        ("Tuần 4", "Tự thêm một feature nhỏ: rule mới, endpoint mới, test mới."),
    ]
    for i, (label, body) in enumerate(weeks):
        x = 110 + i * 365
        y = 230
        rounded_box(draw, (x, y, x + 300, y + 300), ["#E8EEF5", "#DFF3E3", "#FFF4CC", "#EEE8FA"][i], "#B7C7D9")
        draw.text((x + 24, y + 24), label, font=label_font, fill="#0B2545")
        draw_wrapped(draw, body, (x + 24, y + 82), 245, body_font, "#1F2937")
        if i < 3:
            arrow(draw, (x + 300, y + 150), (x + 360, y + 150))
    draw.text((110, 650), "Nguyên tắc học: mỗi ngày đọc một file, chạy một script, ghi lại một câu hỏi, sửa một thứ nhỏ.", font=body_font, fill="#334155")
    img.save(path)


def create_assets() -> dict[str, Path]:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    assets = {
        "system_map": ASSET_DIR / "system_map.png",
        "request_flow": ASSET_DIR / "request_flow.png",
        "ai_pipeline": ASSET_DIR / "ai_pipeline.png",
        "learning_roadmap": ASSET_DIR / "learning_roadmap.png",
    }
    make_system_map(assets["system_map"])
    make_request_flow(assets["request_flow"])
    make_ai_pipeline(assets["ai_pipeline"])
    make_learning_roadmap(assets["learning_roadmap"])
    return assets


def add_picture(doc: Document, path: Path, caption: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(path), width=Inches(6.4))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = cap.add_run(caption)
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor.from_string("555555")


def add_code_block(doc: Document, code: str) -> None:
    table = doc.add_table(rows=1, cols=1)
    set_table_borders(table, "DADCE0")
    cell = table.cell(0, 0)
    set_cell_shading(cell, "F8FAFC")
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(code.strip())
    run.font.name = "Consolas"
    run.font.size = Pt(9)


def build_document() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    assets = create_assets()
    doc = Document()
    configure_styles(doc)
    add_title(doc)
    add_picture(doc, assets["system_map"], "Hinh 1. Ban do he thong de ban nhin thay toan canh truoc khi doc code.")

    doc.add_heading("Mục Lục Dạng Tab", level=1)
    add_table(
        doc,
        ["Tab", "Chủ đề", "Kết quả sau khi đọc"],
        [
            ["Tab 0", "Cách học và cách dùng tài liệu", "Biết nên đọc theo thứ tự nào, không bị ngợp."],
            ["Tab 1", "Bức tranh tổng quan dự án", "Giải thích dự án cho người khác bằng ngôn ngữ đơn giản."],
            ["Tab 2", "Nền tảng Python cần biết", "Đọc được function, class, schema, service."],
            ["Tab 3", "Backend FastAPI", "Hiểu endpoint, request, response, status code."],
            ["Tab 4", "AI Engineer trong dự án", "Hiểu prompt, RAG, structured output, fallback."],
            ["Tab 5", "Data, guardrail và evaluation", "Biết vì sao AI phải được kiểm soát."],
            ["Tab 6", "Test và cách tự tin thay đổi code", "Biết chạy smoke test và đọc kết quả."],
            ["Tab 7", "Lộ trình tự học và ra quyết định", "Có kế hoạch học và phát triển dự án tiếp."],
        ],
        [0.75, 2.15, 3.6],
    )

    add_tab_header(
        doc,
        "Tab 0",
        "Cách Học Nếu Bạn Chưa Biết Python Hay AI",
        "Tab này giúp bạn học đúng cách: không học tất cả cùng lúc, mà đi từ đường request, đến code, đến AI, đến cách quyết định.",
    )
    doc.add_paragraph(
        "Bạn đang dùng một cách học rất tốt: có trí tưởng tượng trước, sau đó xây nền tảng để trí tưởng tượng có chỗ bám. Backend và AI không phải phép màu. Nó là một chuỗi quy trình: nhận dữ liệu, kiểm tra, xử lý, gọi AI nếu cần, kiểm soát kết quả, và trả lại output có cấu trúc."
    )
    callout(
        doc,
        "Cách đọc mỗi ngày",
        "Mỗi ngày chỉ cần làm 3 việc: đọc một mục trong tài liệu, mở file code được nhắc đến, chạy một script test. Nếu bạn làm đủ 30 ngày, bạn sẽ có nền tảng thật sự.",
        fill=YELLOW,
    )
    add_steps(
        doc,
        [
            "Đọc phần giải thích bằng ngôn ngữ người mới.",
            "Mở file code được chỉ định và tìm đúng function/class.",
            "Chạy script test liên quan để thấy code sống như thế nào.",
            "Ghi lại một câu hỏi: tại sao phải làm như vậy?",
            "Thử thay đổi nhỏ ở bản copy hoặc branch riêng khi đã sẵn sàng.",
        ],
    )

    add_tab_header(
        doc,
        "Tab 1",
        "Bức Tranh Tổng Quan Dự Án",
        "Tab này trả lời câu hỏi: dự án này là gì, người dùng đi vào đâu, AI nằm ở đâu, data và rule có vai trò gì.",
    )
    doc.add_paragraph(
        "Dự án AI Nutrition Coach backend tạo công thức smoothie cá nhân hóa cho người trưởng thành Việt Nam bị thừa cân/béo phì. Backend không chỉ hỏi AI rồi trả kết quả. Backend phải kiểm tra scope nghiên cứu, lọc dị ứng, lấy data trái cây, tạo công thức, đánh giá dinh dưỡng, và trả về decision."
    )
    add_picture(doc, assets["request_flow"], "Hình 2. Đường đi của một request từ người dùng đến kết quả.")
    add_table(
        doc,
        ["Thành phần", "Nó làm gì", "File nên mở"],
        [
            ["API", "Nơi frontend hoặc tester gọi vào backend.", "app/main.py"],
            ["Schema", "Định nghĩa dữ liệu hợp lệ và response trả ra.", "app/schemas/*.py"],
            ["Service", "Chứa logic nghiệp vụ thật sự.", "app/services/*.py"],
            ["Agent graph", "Điều phối các bước AI tạo smoothie.", "app/agents/*.py"],
            ["Data seed", "Dữ liệu fallback khi chưa có DB/vector.", "data/*.json"],
            ["Tests", "Bằng chứng hệ thống vẫn chạy đúng.", "scripts/test_*.py"],
        ],
        [1.1, 2.9, 2.5],
    )

    add_tab_header(
        doc,
        "Tab 2",
        "Nền Tảng Python Cần Biết Để Đọc Dự Án",
        "Tab này không dạy Python từ A-Z. Nó dạy đúng những thứ bạn cần để đọc backend hiện tại.",
    )
    add_table(
        doc,
        ["Khái niệm", "Hiểu đơn giản", "Ví dụ trong dự án"],
        [
            ["Function", "Một hành động có tên, nhận input và trả output.", "build_profile_analysis(profile)"],
            ["Class", "Một hộp chứa dữ liệu hoặc hành vi.", "NutritionService, EvaluationService"],
            ["Type hint", "Ghi chú kiểu dữ liệu để code dễ đọc hơn.", "profile: ProfileInput"],
            ["Dataclass", "Class gọn để lưu data nội bộ.", "ThresholdRule, SafetyRule"],
            ["Exception", "Cách báo lỗi có ý nghĩa.", "ResearchScopeError"],
            ["Import", "Lấy code từ file khác để dùng.", "from app.services..."],
        ],
        [1.2, 2.6, 2.7],
    )
    add_code_block(
        doc,
        """
def build_profile_analysis(profile: ProfileInput) -> ProfileAnalysisResponse:
    bmi = round(profile.weight_kg / ((profile.height_cm / 100) ** 2), 2)
    ...
    return ProfileAnalysisResponse(...)
        """,
    )
    doc.add_paragraph(
        "Đọc function trên như đọc một câu tiếng Việt: đưa vào profile, tính BMI, xếp loại, rồi trả về ProfileAnalysisResponse. Khi mới học, bạn không cần hiểu từng ký tự. Hãy hỏi: input là gì, xử lý gì, output là gì."
    )

    add_tab_header(
        doc,
        "Tab 3",
        "Backend FastAPI: Cửa Ra Vào Của Hệ Thống",
        "Tab này giúp bạn hiểu endpoint, request, response và cách backend nói chuyện với frontend.",
    )
    doc.add_paragraph(
        "FastAPI là framework giúp tạo API bằng Python. Trong dự án này, file app/main.py là cửa chính. Mỗi dòng @app.get hoặc @app.post là một endpoint."
    )
    add_table(
        doc,
        ["Endpoint", "Dùng để làm gì", "Người mới nên test khi nào"],
        [
            ["GET /health", "Kiểm tra app sống hay không.", "Ngay sau khi start server."],
            ["GET /system-status", "Xem OpenAI, DB, vector, fallback có sẵn sàng không.", "Trước demo hoặc debug."],
            ["POST /profiles/analyze", "Tính BMI và scope.", "Khi muốn xem user có đúng phạm vi nghiên cứu không."],
            ["POST /knowledge/search-preview", "Xem RAG/fallback lấy data gì.", "Khi nghi AI dùng sai nguyên liệu."],
            ["POST /smoothies/generate", "Tạo công thức smoothie.", "Khi cần output chính."],
            ["POST /smoothies/evaluate", "Chấm điểm một công thức có sẵn.", "Khi muốn QA kết quả."],
            ["POST /smoothies/generate-and-evaluate", "Tạo và chấm điểm trong một lần.", "Khi demo end-to-end."],
        ],
        [1.8, 3.0, 1.7],
    )
    callout(
        doc,
        "Tư duy backend",
        "Backend tốt không phải chỉ là có API. Backend tốt phải có contract rõ ràng, lỗi rõ ràng, test rõ ràng, và không để AI tự do tạo kết quả nguy hiểm.",
        fill=GREEN,
    )

    add_tab_header(
        doc,
        "Tab 4",
        "AI Engineer Trong Dự Án Này",
        "Tab này giải thích AI không phải một nút bấm mà là một pipeline có data, prompt, schema, fallback và kiểm soát.",
    )
    add_picture(doc, assets["ai_pipeline"], "Hình 3. Pipeline AI được đặt bên trong backend, không đứng riêng lẻ.")
    add_table(
        doc,
        ["Khái niệm AI", "Trong dự án này nghĩa là gì", "File liên quan"],
        [
            ["Prompt", "Cách ta nói với model: mục tiêu, ràng buộc, context.", "app/agents/prompts.py"],
            ["Structured output", "Bắt AI trả về đúng schema, không trả văn bản lung tung.", "app/schemas/smoothie_schema.py"],
            ["RAG", "Lấy kiến thức từ data trước khi hỏi AI.", "app/services/vector_service.py"],
            ["Fallback", "Không có API key vẫn có output mẫu để dev/test.", "app/agents/nodes.py"],
            ["Graph", "Chia AI flow thành các node: analyze, generate, safety.", "app/agents/nutrition_graph.py"],
        ],
        [1.35, 3.45, 1.7],
    )
    doc.add_paragraph(
        "Quyết định quan trọng của AI Engineer là không hỏi model một cách mơ hồ. Ta phải dựa vào schema, prompt, knowledge context, guardrail và evaluation. Khi đó AI trở thành một thành phần trong hệ thống, không phải cả hệ thống."
    )

    add_tab_header(
        doc,
        "Tab 5",
        "Data, Guardrail Và Evaluation",
        "Tab này giúp bạn hiểu vì sao data chưa xong vẫn có thể làm P2/P3, và vì sao AI cần được chấm điểm sau khi tạo.",
    )
    add_table(
        doc,
        ["Lớp", "Câu hỏi nó trả lời", "Ví dụ"],
        [
            ["Data", "Ta đưa cho AI kiến thức nào?", "vietnamese_fruits_seed.json"],
            ["Guardrail", "Có vi phạm điều cấm không?", "Dị ứng sữa, không thích chuối."],
            ["Threshold", "Công thức có đạt ngưỡng dinh dưỡng không?", "Protein >= 8g, sugar <= 25g."],
            ["Safety rule", "Có cần cảnh báo y tế không?", "Medical notes present."],
            ["Evaluation report", "Kết quả nên pass, review hay reject?", "score, decision, issues."],
        ],
        [1.4, 3.1, 2.0],
    )
    callout(
        doc,
        "Điểm rất quan trọng",
        "AI có thể nói nghe hợp lý nhưng vẫn sai. Vì vậy, sau generate phải có evaluation. Sau evaluation phải có decision: pass, review, reject. Đây là tư duy AI Engineer chuyên nghiệp.",
        fill=RED,
    )

    add_tab_header(
        doc,
        "Tab 6",
        "Test: Cách Tự Tin Thay Đổi Dự Án",
        "Tab này dạy bạn cách biết code còn chạy đúng hay không sau khi sửa.",
    )
    add_code_block(
        doc,
        """
cd D:\\Project\\AI\\backend
D:\\Project\\AI\\.venv\\Scripts\\python.exe scripts\\test_p2_p3_smoke.py
        """,
    )
    add_table(
        doc,
        ["Script", "Nó kiểm tra gì"],
        [
            ["test_openapi_contract.py", "API schema và endpoint còn đúng contract không."],
            ["test_guardrail_and_prompt.py", "Prompt và guardrail có chặn đúng ràng buộc không."],
            ["test_evaluation_edge_cases.py", "Pass/review/reject có đúng trong ca xấu không."],
            ["test_generate_and_evaluate_api.py", "Luồng end-to-end API có chạy được không."],
            ["test_p2_p3_smoke.py", "Chạy gom nhiều test quan trọng trong một lệnh."],
        ],
        [2.2, 4.3],
    )
    doc.add_paragraph(
        "Người mới hay sợ sửa code vì không biết mình làm hỏng gì. Test là lan can an toàn. Khi bạn thêm một feature, hãy tự hỏi: nếu sai thì test nào bắt được?"
    )

    add_tab_header(
        doc,
        "Tab 7",
        "Lộ Trình Tự Học Và Ra Quyết Định Phát Triển",
        "Tab này biến dự án thành giáo trình 30 ngày và bộ câu hỏi để bạn quyết định tương lai.",
    )
    add_picture(doc, assets["learning_roadmap"], "Hình 4. Lộ trình học 30 ngày dựa trên chính dự án của bạn.")
    add_table(
        doc,
        ["Khi muốn...", "Hãy quyết định dựa trên...", "Ví dụ quyết định tốt"],
        [
            ["Thêm data", "Schema có cần thêm field không, source có đáng tin không.", "Thêm cột source_id và quality_status trước khi import."],
            ["Thêm AI feature", "Output có schema và test không.", "Thêm endpoint recommend ingredient nhưng có response model."],
            ["Dùng OpenAI live", "Có API key, cost, fallback, error handling chưa.", "Chỉ bật live call sau khi dry-run pass."],
            ["Dùng vector DB", "Data đã sạch và có embedding chưa.", "Import fruit data trước, embed sau."],
            ["Cho chuyên gia review", "Có evaluation report để đọc nhanh không.", "Gửi score, issues, recommendations."],
        ],
        [1.4, 2.65, 2.45],
    )
    callout(
        doc,
        "Bài tập cấp độ 1",
        "Mở app/main.py và tìm endpoint /profiles/analyze. Sau đó mở nutrition_service.py và tìm build_profile_analysis. Hãy vẽ lại bằng tay: input nào vào, output nào ra.",
        fill=YELLOW,
    )
    callout(
        doc,
        "Bài tập cấp độ 2",
        "Mở evaluation_service.py. Tìm hàm build_evaluation_report. Hãy giải thích bằng tiếng Việt: khi nào pass, khi nào review, khi nào reject.",
        fill=YELLOW,
    )
    callout(
        doc,
        "Bài tập cấp độ 3",
        "Tự nghĩ một feature nhỏ: ví dụ thêm rule cảnh báo đường cao. Trước khi code, viết ra schema, service, test. Đây là cách AI/backend engineer làm việc.",
        fill=YELLOW,
    )

    doc.add_heading("Phụ Lục A. Bản Đồ File Nên Đọc Theo Thứ Tự", level=1)
    add_table(
        doc,
        ["Thứ tự", "File", "Lý do đọc"],
        [
            ["1", "backend/README.md", "Biết cách setup, chạy, test."],
            ["2", "app/main.py", "Biết API vào/ra ở đâu."],
            ["3", "app/schemas/profile_schema.py", "Hiểu input user."],
            ["4", "app/schemas/smoothie_schema.py", "Hiểu output smoothie."],
            ["5", "app/services/nutrition_service.py", "Hiểu flow nghiệp vụ chính."],
            ["6", "app/agents/prompts.py", "Hiểu cách nói với AI."],
            ["7", "app/services/guardrail_service.py", "Hiểu an toàn và ràng buộc."],
            ["8", "app/services/evaluation_service.py", "Hiểu chấm điểm kết quả."],
            ["9", "scripts/test_p2_p3_smoke.py", "Hiểu cách kiểm chứng hệ thống."],
        ],
        [0.65, 2.65, 3.2],
    )

    doc.add_heading("Phụ Lục B. Từ Điển Nhanh", level=1)
    add_table(
        doc,
        ["Từ", "Giải thích ngắn"],
        [
            ["API", "Cửa để ứng dụng khác gửi request vào backend."],
            ["Endpoint", "Một đường API cụ thể, ví dụ /smoothies/generate."],
            ["Schema", "Hợp đồng dữ liệu: field nào bắt buộc, kiểu gì."],
            ["Service", "Nơi chứa logic nghiệp vụ."],
            ["RAG", "Lấy data liên quan rồi đưa vào prompt cho AI."],
            ["Prompt", "Hướng dẫn gửi cho AI."],
            ["Structured output", "Bắt AI trả kết quả theo format có cấu trúc."],
            ["Guardrail", "Lớp chặn lỗi/nguy cơ trước khi trả kết quả."],
            ["Evaluation", "Chấm điểm kết quả sau khi generate."],
            ["Smoke test", "Bộ test nhanh để biết hệ thống còn ổn không."],
        ],
        [1.7, 4.8],
    )

    doc.add_heading("Kết Lại", level=1)
    doc.add_paragraph(
        "Bạn không cần học backend và AI bằng cách nhồi hết lý thuyết. Hãy học bằng dự án này. Mỗi lần đọc một file, bạn hỏi: file này nhận gì, xử lý gì, trả gì, và nếu sai thì test nào bắt được. Khi cách nghĩ đó thành phản xạ, bạn đã có nền tảng để biến trí tưởng tượng thành sản phẩm."
    )

    footer = doc.sections[0].footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("AI Nutrition Coach - Learning Guide").font.size = Pt(9)

    doc.save(OUTPUT_PATH)


if __name__ == "__main__":
    build_document()
    print(OUTPUT_PATH)
