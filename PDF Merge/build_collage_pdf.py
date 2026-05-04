"""

สร้าง PDF หนึ่งไฟล์: แต่ละโฟลเดอร์ย่อยของโฟลเดอร์ที่วางสคริปต์นี้ = หนึ่งหน้า (เรียงรูปเป็นตาราง)



วิธีใช้: คัดลอก build_collage_pdf.py กับ RUN_collage_to_PDF.bat ไปไว้ในโฟลเดอร์หลักที่มีแต่โฟลเดอร์ย่อย (หรือโฟลเดอร์ย่อยที่มีรูป)

แล้วดับเบิลคลิก .bat หรือรัน: python build_collage_pdf.py



ไม่พึ่ง working directory — ใช้ตำแหน่งไฟล์สคริปต์เป็นรากเสมอ

"""

from __future__ import annotations



import math

import sys

from pathlib import Path



from PIL import Image, ImageDraw, ImageFont



ROOT = Path(__file__).resolve().parent

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

SKIP_DIR_NAMES = frozenset(

    {"__pycache__", ".git", ".hg", ".svn", ".venv", "venv", "node_modules"}

)



# A4 @ 200 DPI

DPI = 200

PAGE_W = int(210 / 25.4 * DPI)
PAGE_H = int(297 / 25.4 * DPI)
MARGIN = 36
TITLE_H = 88
BG = (255, 255, 255)


def truetype_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        r"C:\Windows\Fonts\seguiui.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def list_subfolders(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in root.iterdir():
        if not p.is_dir():
            continue
        if p.name.startswith("."):
            continue
        if p.name in SKIP_DIR_NAMES:
            continue
        out.append(p)

    def sort_key(p: Path) -> tuple:
        name = p.name
        if name.isdigit():
            return (0, int(name), "")
        return (1, name.lower())

    out.sort(key=sort_key)
    return out


def list_images(folder: Path) -> list[Path]:
    files: list[Path] = []
    for p in folder.iterdir():
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            files.append(p)
    return sorted(files, key=lambda x: x.name.lower())


def grid_dims(n: int) -> tuple[int, int]:
    if n <= 0:
        return 1, 1
    cols = max(1, math.ceil(math.sqrt(n)))
    rows = math.ceil(n / cols)
    return cols, rows


def fit_image(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    scale = min(max_w / w, max_h / h, 1.0)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    return img.resize((nw, nh), Image.Resampling.LANCZOS)


def draw_fitted_title(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    max_width: int,
    margin: int,
) -> int:
    """วาดหัวข้อให้พอดีความกว้าง คืนค่าความสูงรวมของบล็อกข้อความ"""
    size = 36
    min_size = 20
    font = truetype_font(size)
    while size >= min_size:
        font = truetype_font(size)
        bbox = draw.textbbox((margin, y), text, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            draw.text((margin, y), text, fill=(20, 20, 20), font=font)
            return bbox[3] - bbox[0]
        size -= 2
    font = truetype_font(min_size)
    draw.text((margin, y), text, fill=(20, 20, 20), font=font)
    bbox = draw.textbbox((margin, y), text, font=font)
    return bbox[3] - bbox[0]


def build_page(
    folder: Path,
    paths: list[Path],
    page_num: int,
    total_pages: int,
) -> Image.Image:
    page = Image.new("RGB", (PAGE_W, PAGE_H), BG)
    draw = ImageDraw.Draw(page)

    folder_name = folder.name
    line1 = f"{folder_name}  (หน้า {page_num}/{total_pages})"
    max_w = PAGE_W - 2 * MARGIN
    h1 = draw_fitted_title(draw, line1, 18, max_w, MARGIN)

    font_small = truetype_font(26)
    line2 = f"{len(paths)} รูป"
    draw.text((MARGIN, 22 + h1), line2, fill=(60, 60, 60), font=font_small)

    inner_top = TITLE_H
    inner_w = PAGE_W - 2 * MARGIN
    inner_h = PAGE_H - MARGIN - inner_top

    if not paths:
        draw.text(
            (MARGIN, inner_top),
            "(ไม่มีรูปในโฟลเดอร์นี้)",
            fill=(120, 120, 120),
            font=font_small,
        )
        return page

    cols, rows = grid_dims(len(paths))
    cell_w = inner_w // cols
    cell_h = inner_h // rows
    pad = 8

    for i, path in enumerate(paths):
        r, c = divmod(i, cols)
        x0 = MARGIN + c * cell_w
        y0 = inner_top + r * cell_h
        with Image.open(path) as im:
            thumb = fit_image(im, cell_w - 2 * pad, cell_h - 2 * pad)
        tw, th = thumb.size
        px = x0 + (cell_w - tw) // 2
        py = y0 + (cell_h - th) // 2
        page.paste(thumb, (px, py))

    return page


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    subfolders = list_subfolders(ROOT)
    if not subfolders:
        print(
            "No subfolders found here. Put this script next to child folders, "
            "or add at least one subfolder (hidden/dot folders are ignored).",
            file=sys.stderr,
        )
        return 1

    out_pdf = ROOT / f"{ROOT.name}_collage.pdf"
    total = len(subfolders)
    pages = [build_page(d, list_images(d), i + 1, total) for i, d in enumerate(subfolders)]

    first, *rest = pages
    first.save(
        out_pdf,
        "PDF",
        resolution=DPI,
        save_all=True,
        append_images=rest,
    )
    # Avoid UnicodeEncodeError on legacy Windows consoles
    try:
        print(f"สร้างแล้ว: {out_pdf}")
        print(f"จำนวนหน้า: {total} — {', '.join(p.name for p in subfolders)}")
    except UnicodeEncodeError:
        print(f"Wrote: {out_pdf}")
        print(f"Pages: {total} | folders: {', '.join(p.name for p in subfolders)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
