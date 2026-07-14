# -*- coding: utf-8 -*-
"""สร้าง app/sso_meta_data.py จากไฟล์ สปส. ของหมิว (แท็บ "บันทึกประเภทพนักงาน").

ใช้ตอนหมิวเพิ่ม/แก้คนในทะเบียนของเธอ แล้วอยากให้ export ของระบบตามทัน:
    python ProjectYK_System/tools/build_sso_meta.py "<path ไฟล์ 2569 เงินสมทบประกันสังคม รวม.xlsx>"

เก็บ: เลขบัตร (id_card), คำนำหน้า, ชื่อ, นามสกุล, ประเภท (ป้ายภายในของหมิว ไม่มีผลเงิน)
— ระบบใช้ match พนักงานด้วยเลขบัตรก่อน แล้วค่อยชื่อ-สกุล.
เขียนเป็น .py (ไม่ใช่ json/static) เพราะ deploy_mvp.sh ก็อปเฉพาะ app/*.py และ
เลขบัตรเป็นข้อมูลส่วนตัว ห้ามไปอยู่ static/ ที่เปิดสาธารณะ.
"""
import sys
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "app" / "sso_meta_data.py"
SHEET = "บันทึกประเภทพนักงาน"

HEADER = '''# -*- coding: utf-8 -*-
"""ทะเบียนคน สปส. ของหมิว (generate จาก tools/build_sso_meta.py — อย่าแก้มือ).

(id_card, prefix, first, last, type) — type เป็นป้ายภายในของหมิว ไม่มีผลเงิน.
"""

PEOPLE = [
'''


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: build_sso_meta.py <xlsx path>")
    wb = openpyxl.load_workbook(sys.argv[1], data_only=True)
    ws = wb[SHEET]
    lines = []
    for row in ws.iter_rows(min_row=2):
        idc = row[0].value  # A
        if idc is None:
            continue
        idc = str(idc).strip().replace("-", "").replace(" ", "")
        first = str(row[2].value or "").strip()   # C
        last = str(row[3].value or "").strip()    # D
        ptype = str(row[8].value or "").strip() if len(row) > 8 else ""  # I
        if not (first or last):
            continue
        rec = (idc, str(row[1].value or "").strip(), first, last, ptype)
        lines.append(f"    {rec!r},\n")
    OUT.write_text(HEADER + "".join(lines) + "]\n", encoding="utf-8")
    print(f"wrote {len(lines)} people -> {OUT}")


if __name__ == "__main__":
    main()
