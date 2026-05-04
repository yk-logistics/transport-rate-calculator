# -*- coding: utf-8 -*-
"""Hero trips + inline Excel per section; remove color legend + global export panel."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "Oatside" / "build_oatside_reports.py"


def main() -> None:
    s = P.read_text(encoding="utf-8")
    if "def _xlsx_dl(" in s:
        print("already patched")
        return

    lines = s.splitlines(True)
    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith("def html_export_downloads_block"))
    except StopIteration as e:
        raise SystemExit("html_export_downloads_block not found") from e
    ret_i = next(
        i
        for i in range(start, len(lines))
        if lines[i].lstrip().startswith("return ") and "join(parts)" in lines[i]
    )
    end = next(i for i in range(ret_i + 1, len(lines)) if lines[i].startswith("# ---"))
    s = "".join(lines[:start] + lines[end:])

    anchor = "    idx = f\"\"\"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>\n"
    if anchor not in s:
        raise SystemExit("idx anchor not found")
    insert = (
        "    def _xlsx_dl(fname: str, short: str) -> str:\n"
        "        return (\n"
        "            \"<a class='xlsx-dl' href='exports/\"\n"
        "            + str(fname)\n"
        "            + \"' download onclick='event.stopPropagation()'>ดาวน์โหลด \"\n"
        "            + html_module.escape(str(short), quote=False)\n"
        "            + \"</a>\"\n"
        "        )\n\n"
        + anchor
    )
    s = s.replace(anchor, insert, 1)

    s = s.replace(
        "<div class='nav'><a href='trips.html'>ดูเที่ยวทั้งหมด</a></div>\n"
        "{html_export_downloads_block()}\n"
        "<div class='grid'>",
        "<div class='hero-trips'><div class='hero-copy'><div class='hero-tag'>แนะนำสำหรับลูกค้า</div>"
        "<div class='hero-title'>เริ่มจากรายการเที่ยวทั้งหมด</div>"
        "<div class='hero-sub'>เวลาเข้า-ออกครบ · ค่าขนส่ง / ส่วนเพิ่ม / ขากลับ — กรองทะเบียนได้ · "
        "ดาวน์โหลด Excel รายเที่ยวละเอียดได้จากปุ่มขวาบนหัวตารางในหน้าเที่ยวทั้งหมด</div></div>"
        "<a class='btn-primary' href='trips.html'>เปิดเที่ยวทั้งหมด</a></div>"
        "<div class='nav-secondary'><a href='trips.html'>ดูเที่ยวทั้งหมด</a> · "
        "<a href='../../../Oatside/Oatside_PG_Trip_Summary_By_Site.xlsx'>ดาวน์โหลด Excel รวมทุกชีต</a></div>\n"
        "<div class='grid'>",
        1,
    )

    color_block = (
        "<details class='section-fold'><summary class='section-sum'>คำอธิบายสี / ไฮไลต์ชั่วโมงรอ</summary>\n"
        "<div class='panel'><p class='sub'><b>สีไฮไลต์:</b> เหลืองอ่อน = รอต้นทางนาน ≥ {_hi_o:g} ชม.; ส้มอ่อน = รอปลายทางนาน ≥ {_hi_d:g} ชม. (ตรวจก่อนตัดสินใจเก็บลูกค้า)</p></div>\n"
        "</details>\n"
    )
    if color_block not in s:
        raise SystemExit("color legend block not found")
    s = s.replace(color_block, "", 1)

    s = s.replace(
        "<details class='section-fold'><summary class='section-sum'>(1) จำนวนเที่ยวต่อวัน (matched Dest_In)</summary>",
        "<details class='section-fold'><summary class='section-sum section-sum-row'>"
        "<span class='sum-main'>(1) จำนวนเที่ยวต่อวัน (matched Dest_In)</span>"
        "<span class='sum-dl'>{_xlsx_dl('01_CPD_MatchedTripsPerDay.xlsx', 'ตาราง (1)')}</span></summary>",
        1,
    )
    s = s.replace(
        "<details class='section-fold'><summary class='section-sum'>(2) เดลี่รถทุกคัน — Dest_In × ทะเบียน</summary>",
        "<details class='section-fold'><summary class='section-sum section-sum-row'>"
        "<span class='sum-main'>(2) เดลี่รถทุกคัน — Dest_In × ทะเบียน</span>"
        "<span class='sum-dl'>{_xlsx_dl('02_Plate_DestDay_Daily.xlsx', 'ตาราง (2)')}</span></summary>",
        1,
    )
    s = s.replace(
        "<details class='section-fold'><summary class='section-sum'>(3) Unmatched — {len(unmatched)} legs เรียงตามเวลา</summary>",
        "<details class='section-fold'><summary class='section-sum section-sum-row'>"
        "<span class='sum-main'>(3) Unmatched — {len(unmatched)} legs เรียงตามเวลา</span>"
        "<span class='sum-dl'>{_xlsx_dl('03_Unmatched_Legs.xlsx', 'ตาราง (3)')}</span></summary>",
        1,
    )
    s = s.replace(
        "<details class='section-fold'><summary class='section-sum'>Audit Log — เหตุผลการคิดเงิน รายวัน × ทะเบียน (คลิกเพื่อขยาย)</summary>",
        "<details class='section-fold'><summary class='section-sum section-sum-row'>"
        "<span class='sum-main'>Audit Log — เหตุผลการคิดเงิน รายวัน × ทะเบียน (คลิกเพื่อขยาย)</span>"
        "<span class='sum-dl'>{_xlsx_dl('04_Audit_Log.xlsx', 'Audit')}</span></summary>",
        1,
    )
    s = s.replace(
        "<details class='section-fold'><summary class='section-sum'>รายทะเบียน</summary>",
        "<details class='section-fold'><summary class='section-sum section-sum-row'>"
        "<span class='sum-main'>รายทะเบียน</span>"
        "<span class='sum-dl'>{_xlsx_dl('02_Plate_DestDay_Daily.xlsx', 'เดลี่×ทะเบียน')}</span></summary>",
        1,
    )

    s = s.replace(
        "<div class='h1'>เที่ยวทั้งหมด</div>\n<div class='nav'><a href='index.html'>&larr; กลับสรุป</a></div>\n",
        "<div class='h1'>เที่ยวทั้งหมด <span class='trips-tag'>หน้าหลักลูกค้า</span></div>\n"
        "<div class='trips-lead'>เวลาเข้า-ออกครบทุกขา · ค่าขนส่ง / เสียเวลา / ขากลับ — กรองทะเบียนได้ด้านล่าง</div>\n"
        "<div class='nav'><a href='index.html'>&larr; สรุปภาพรวม</a> · "
        "<a href='../../../Oatside/Oatside_PG_Trip_Summary_By_Site.xlsx'>Excel รวมทุกชีต</a></div>\n",
        1,
    )

    s = s.replace(
        "<div class='panel'><h3>เที่ยวทั้งหมด (matched + unmatched)</h3>\n",
        "<div class='panel'><div class='panel-title-row'><h3>เที่ยวทั้งหมด (matched + unmatched)</h3>"
        "<a class='xlsx-dl' href='exports/05_Trip_Detail.xlsx' download onclick='event.stopPropagation()'>"
        "ดาวน์โหลด Excel (Trip Detail)</a></div>\n",
        1,
    )

    css_old = (
        "\".export-panel{border:1px solid #c5d0e0;border-radius:12px;background:linear-gradient(180deg,#fbfdff,#eef4fb)}\""
        "\".export-list{margin:8px 0 0 18px;line-height:1.75}\""
        "\n    )"
    )
    css_new = (
        "\".section-sum-row{display:flex;justify-content:space-between;align-items:center;gap:12px}\""
        "\"summary.section-sum-row .sum-main{flex:1;text-align:left}\""
        "\"summary.section-sum-row .sum-dl{flex-shrink:0}\""
        "\".xlsx-dl{font-size:12px;font-weight:700;color:#0b57d0;padding:5px 10px;border-radius:8px;border:1px solid #b8cff4;background:#eef5ff;white-space:nowrap}\""
        "\".hero-trips{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:14px;background:linear-gradient(135deg,#e8f1ff,#ffffff);border:1px solid #c5d0e0;border-radius:12px;padding:16px 18px;margin:12px 0 16px}\""
        "\".hero-copy{max-width:720px}\""
        "\".hero-tag{display:inline-block;font-size:11px;font-weight:700;color:#0b57d0;background:#e3eeff;border-radius:999px;padding:2px 10px;margin-bottom:6px}\""
        "\".hero-title{font-size:20px;font-weight:800;color:#12243b;margin-bottom:4px}\""
        "\".hero-sub{color:#4b5b74;font-size:13px;line-height:1.45}\""
        "\".btn-primary{display:inline-block;padding:12px 18px;border-radius:10px;background:#0b57d0;color:#fff;font-weight:800;box-shadow:0 4px 12px rgba(11,87,208,.22)}\""
        "\".btn-primary:hover{filter:brightness(1.05)}\""
        "\".nav-secondary{margin:0 0 12px;font-size:13px;color:#4b5b74}\""
        "\".panel-title-row{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}\""
        "\".panel-title-row h3{margin:0}\""
        "\".h1 .trips-tag{font-size:13px;font-weight:800;color:#0b57d0;margin-left:8px;vertical-align:middle}\""
        "\".trips-lead{color:#4b5b74;font-size:14px;margin:-2px 0 10px}\""
        "\n    )"
    )
    if css_old not in s:
        raise SystemExit("css export-panel block not found")
    s = s.replace(css_old, css_new, 1)

    P.write_text(s, encoding="utf-8")
    print("patched", P)


if __name__ == "__main__":
    main()
