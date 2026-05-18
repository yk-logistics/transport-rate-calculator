"""
Generate blank DLT Log Book form as PNG and PDF.

Output:
- ProjectYK_System/docs/forms/DLT_LogBook_Blank.png
- ProjectYK_System/docs/forms/DLT_LogBook_Blank.pdf
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from generate_dlt_logbook_exact import INTERVALS, SECTIONS, SUB_COLS

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "forms"
PNG_FILE = OUT_DIR / "DLT_LogBook_Blank.png"
PDF_FILE = OUT_DIR / "DLT_LogBook_Blank.pdf"

A4_W, A4_H = 2480, 3508  # 300 DPI
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

FONT_REGULAR = Path("C:/Windows/Fonts/tahoma.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/tahomabd.ttf")


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold and FONT_BOLD.exists() else FONT_REGULAR
    return ImageFont.truetype(str(path), size)


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    if not text:
        return 0, 0
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words = text.split(" ")
    lines: list[str] = []
    cur = ""
    for word in words:
        candidate = word if not cur else f"{cur} {word}"
        if text_size(draw, candidate, fnt)[0] <= max_w:
            cur = candidate
            continue
        if cur:
            lines.append(cur)
        cur = word

        # Thai text often has no spaces; split long chunks by character if needed.
        if text_size(draw, cur, fnt)[0] > max_w:
            chunk = ""
            for ch in cur:
                candidate = chunk + ch
                if text_size(draw, candidate, fnt)[0] <= max_w:
                    chunk = candidate
                else:
                    if chunk:
                        lines.append(chunk)
                    chunk = ch
            cur = chunk
    if cur:
        lines.append(cur)
    return lines


def draw_center(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    *,
    line_gap: int = 2,
) -> None:
    x1, y1, x2, y2 = box
    lines = wrap_text(draw, text, fnt, max(1, x2 - x1 - 8))
    line_heights = [text_size(draw, line, fnt)[1] for line in lines]
    total_h = sum(line_heights) + line_gap * max(0, len(lines) - 1)
    y = y1 + ((y2 - y1) - total_h) / 2
    for line, h in zip(lines, line_heights):
        w, _ = text_size(draw, line, fnt)
        draw.text((x1 + ((x2 - x1) - w) / 2, y), line, fill=BLACK, font=fnt)
        y += h + line_gap


def draw_left(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    *,
    pad: int = 8,
    line_gap: int = 2,
) -> None:
    x1, y1, x2, y2 = box
    lines = wrap_text(draw, text, fnt, max(1, x2 - x1 - pad * 2))
    line_heights = [text_size(draw, line, fnt)[1] for line in lines]
    total_h = sum(line_heights) + line_gap * max(0, len(lines) - 1)
    y = y1 + ((y2 - y1) - total_h) / 2
    for line, h in zip(lines, line_heights):
        draw.text((x1 + pad, y), line, fill=BLACK, font=fnt)
        y += h + line_gap


def line(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], width: int = 3) -> None:
    draw.line(xy, fill=BLACK, width=width)


def rect(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], width: int = 3) -> None:
    draw.rectangle(xy, outline=BLACK, width=width)


def build() -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (A4_W, A4_H), WHITE)
    draw = ImageDraw.Draw(img)

    title_font = font(34, bold=True)
    header_font = font(22, bold=True)
    small_font = font(20)
    small_bold = font(20, bold=True)
    tiny_font = font(14)
    body_font = font(20)
    body_bold = font(19, bold=True)

    # Title and blank header fields.
    draw_center(draw, (0, 90, A4_W, 145), "แบบบันทึกผลการบำรุงรักษารถ (Log Book)", title_font)

    y_info = 175
    draw.text((118, y_info), "ผู้ประกอบการขนส่ง........................................................", fill=BLACK, font=small_font)
    draw.text((770, y_info), "ชนิดรถ........................", fill=BLACK, font=small_font)
    draw.text((1030, y_info), "หมายเลขทะเบียน........................", fill=BLACK, font=small_font)
    draw.text((1580, y_info), "เลขไมล์เริ่มต้น........................", fill=BLACK, font=small_font)

    # Table geometry.
    x0, y0 = 115, 245
    table_w = 2250
    no_w, section_w, item_w = 48, 352, 552
    small_w = (table_w - no_w - section_w - item_w) / 12
    x = [x0, x0 + no_w, x0 + no_w + section_w, x0 + no_w + section_w + item_w]
    for _ in range(12):
        x.append(round(x[-1] + small_w))
    x[-1] = x0 + table_w

    header_heights = [48, 44, 42, 42, 42, 42]
    y = [y0]
    for h in header_heights:
        y.append(y[-1] + h)

    body_rows = sum(len(items) for _, _, items in SECTIONS)
    body_h = 1960
    row_h = body_h / body_rows
    for _ in range(body_rows):
        y.append(round(y[-1] + row_h))
    body_end = y[-1]
    sig_end = body_end + 150

    # Outer border and grid.
    rect(draw, (x0, y0, x[-1], sig_end), width=5)

    # Header left cells: the paper form has "รายการ" spanning the section
    # columns, while the item column carries row labels for the interval block.
    rect(draw, (x0, y0, x[2], y[6]), width=3)
    draw_center(draw, (x0, y0, x[2], y[6]), "รายการ", header_font)
    rect(draw, (x[2], y0, x[3], y[6]), width=3)

    # Header rows for intervals.
    for yi in y[:7]:
        line(draw, (x[2], yi, x[-1], yi), width=3)

    # Vertical lines for all interval columns.
    for idx, xi in enumerate(x[3:], start=3):
        w = 5 if idx in (3, 6, 9, 12, 15) else 2
        line(draw, (xi, y0, xi, sig_end), width=w)

    # Left table vertical separators.
    line(draw, (x[1], y[6], x[1], body_end), width=2)
    line(draw, (x[2], y[6], x[2], body_end), width=2)
    line(draw, (x[3], y0, x[3], sig_end), width=5)

    # Header row labels in the item column.
    draw_center(draw, (x[2], y[0], x[3], y[1]), "ทุกระยะทาง 40,000 กม.", small_bold)
    draw_center(draw, (x[2], y[1], x[3], y[2]), "หรือทุกระยะเวลา (เดือน)", small_bold)
    draw_center(draw, (x[2], y[2], x[3], y[4]), "ดำเนินการบำรุงรักษา\nรถเมื่อ", small_bold)
    draw_center(draw, (x[2], y[4], x[3], y[5]), "ระยะทาง", small_font)
    draw_center(draw, (x[2], y[5], x[3], y[6]), "ดำเนินการ", small_font)

    for block, (km_label, month_label) in enumerate(INTERVALS):
        c1 = 3 + block * 3
        c2 = c1 + 3
        draw_center(draw, (x[c1], y[0], x[c2], y[1]), km_label, small_bold)
        draw_center(draw, (x[c1], y[1], x[c2], y[2]), month_label, small_font)
        draw_center(draw, (x[c1], y[3], x[c2], y[4]), "วันที่", small_font)
        draw_center(draw, (x[c1], y[4], x[c2], y[5]), "ระยะทาง", small_font)
        for offset, label in enumerate(SUB_COLS):
            draw_center(draw, (x[c1 + offset], y[5], x[c1 + offset + 1], y[6]), label, tiny_font)

    # Body rows and section merges.
    cur_row = 6
    for section_no, section_name, items in SECTIONS:
        sec_top = y[cur_row]
        sec_bottom = y[cur_row + len(items)]
        rect(draw, (x0, sec_top, x[1], sec_bottom), width=2)
        rect(draw, (x[1], sec_top, x[2], sec_bottom), width=2)
        draw_center(draw, (x0, sec_top, x[1], sec_bottom), str(section_no), body_bold)
        draw_center(draw, (x[1], sec_top, x[2], sec_bottom), section_name, body_bold)

        for item in items:
            row_top, row_bottom = y[cur_row], y[cur_row + 1]
            line(draw, (x[2], row_top, x[-1], row_top), width=2)
            draw_left(draw, (x[2], row_top, x[3], row_bottom), item, body_font, pad=10)
            cur_row += 1

    line(draw, (x0, body_end, x[-1], body_end), width=5)
    # Signature area: blank, no handwritten signature.
    draw_center(
        draw,
        (x0, body_end, x[6], sig_end),
        "ลงชื่อ ผู้ควบคุมการบำรุงรักษารถ",
        body_bold,
    )
    line(draw, (x[6], body_end, x[6], sig_end), width=3)
    line(draw, (x[9], body_end, x[9], sig_end), width=3)
    line(draw, (x[12], body_end, x[12], sig_end), width=3)

    # Note line.
    note_y = sig_end + 160
    draw.text((115, note_y), "หมายเหตุ ..................................................................................................................................................................................", fill=BLACK, font=body_font)

    img.save(PNG_FILE)
    img.save(PDF_FILE, "PDF", resolution=300.0)
    return PNG_FILE, PDF_FILE


if __name__ == "__main__":
    png, pdf = build()
    print("Saved:", png.name, pdf.name)
