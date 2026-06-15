#!/usr/bin/env python3
"""Update Oatside config: May Bangchak diesel anchors, May-only customer report, archive April rules."""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "Oatside" / "oatside_config.json"
BUILD_PATH = ROOT / "Oatside" / "build_oatside_reports.py"
APR_DOC = ROOT / "Oatside" / "docs" / "BILLING_LOCKED_APR2026.md"

# Bangchak historical paste: คอลัมน์ที่ 2 = ไฮดีเซล S (token ที่ 2 หลังวันที่; index 1 แบบ 0-based)
DIESEL_COL_INDEX = 1

PASTE = """
26/05/2569	60.25	41.20	35.20	54.84	33.84	37.90	43.93	44.30
20/05/2569	61.25	42.20	35.20	54.84	33.84	37.90	44.53	44.90
19/05/2569	61.25	42.20	35.20	55.09	33.84	37.90	44.53	44.90
14/05/2569	61.25	41.45	34.45	55.09	32.99	37.05	43.68	44.05
13/05/2569	61.25	40.75	33.75	55.09	32.29	36.35	42.98	43.35
08/05/2569	61.25	39.95	32.95	55.09	31.39	35.45	42.08	42.45
01/05/2569	62.10	40.80	33.80	56.04	32.24	36.30	42.93	43.30
24/04/2569	62.10	40.20	33.20	56.04	31.39	35.45	42.08	42.45
21/04/2569	64.10	41.70	34.70	56.04	31.39	35.45	42.08	42.45
17/04/2569	65.30	42.90	35.90	56.04	31.39	35.45	42.08	42.45
11/04/2569	66.80	44.40	37.40	56.54	31.89	35.95	42.58	42.95
09/04/2569	68.80	48.40	43.40	57.54	34.89	38.95	43.58	43.95
05/04/2569	70.94	50.54	45.54	57.54	34.89	38.95	43.58	43.95
04/04/2569	66.14	47.74	-	57.54	34.89	38.95	43.58	43.95
03/04/2569	66.14	47.74	-	57.54	35.69	38.95	43.58	43.95
02/04/2569	62.14	44.24	-	57.54	34.99	38.25	42.88	43.25
31/03/2569	58.64	40.74	-	57.54	33.79	37.05	41.68	42.05
"""


def th_to_iso(th_date: str) -> str:
    dd, mm, yy = th_date.split("/")
    y = int(yy) - 543
    return f"{y:04d}-{mm}-{dd}"


def parse_paste(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in text.strip().splitlines():
        m = re.search(r"(\d{2}/\d{2}/\d{4})", line)
        if not m:
            continue
        nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", line.split(m.group(1))[1])]
        if len(nums) <= DIESEL_COL_INDEX:
            continue
        iso = th_to_iso(m.group(1))
        out[iso] = nums[DIESEL_COL_INDEX]
    return out


def main() -> None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    parsed = parse_paste(PASTE)

    # Keep April diesel as billed (column 2 from paste = index 1 — already in history)
    existing = {e["date"]: e for e in cfg.get("diesel_price_history", [])}
    may_dates = [d for d in parsed if d.startswith("2026-05")]
    for d in sorted(may_dates):
        existing[d] = {
            "date": d,
            "price": parsed[d],
            "source": "Bangchak historical paste 26.05.2026 — ไฮดีเซล S (คอลัมน์ที่ 5)",
        }
    cfg["diesel_price_history"] = [existing[k] for k in sorted(existing)]

    cfg["report_start_date"] = "2026-05-01"
    cfg["report_end_date"] = "2026-05-31"
    cfg["customer_rate_summary"] = (
        "พ.ค. 2569: ฐาน 6,500 บาท (แถบน้ำมัน 31.00–31.99 บ./ล.) "
        "ปรับ +1.5% ต่อ 1 บาท จากราคาบางจากไฮดีเซล S (carry-forward ระหว่างวันประกาศ)"
    )

    april_rules = [r for r in cfg.get("trip_rates", []) if r.get("from", "").startswith("2026-04")]
    cfg["_billing_locked_april_2026"] = {
        "note": "วางบิลเม.ย. 2569 เรียบร้อย — เก็บอ้างอิงภายใน ไม่แสดงบนหน้ารายงานลูกค้า",
        "report_window": {"from": "2026-04-01", "to": "2026-04-30"},
        "diesel_note": "ใช้ราคาจากคอลัมน์ที่ 2 ของตารางบางจาก (~40–50 บ./ล.) ตาม diesel_price_history เดิม",
        "trip_rates": april_rules,
        "summary": "ฐาน 7,500 บาท (12–15 เม.ย. 8,000) แถบน้ำมัน 50.00–50.99 บ./ล. ปรับ ±1.5%/บาท ไม่ต่ำกว่า 6,500",
    }

    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    APR_DOC.parent.mkdir(parents=True, exist_ok=True)
    APR_DOC.write_text(
        """# Oatside / P&G — เงื่อนไขวางบิล เม.ย. 2569 (ล็อกแล้ว)

> **ไม่แสดงบนหน้ารายงานลูกค้า** — เก็บไว้ให้ทีม YK อ้างอิงเท่านั้น  
> เม.ย. วางบิลลูกค้าเรียบร้อยแล้ว (2026-05-26)

## ช่วงรายงาน
- 2026-04-01 ถึง 2026-04-30

## ค่าขนส่ง (trip_rates)
| ช่วงวันที่ | ฐาน (บาท) | แถบน้ำมัน (บ./ล.) | ปรับ | ขั้นต่ำ |
|------------|-----------|-------------------|------|--------|
| 1–30 เม.ย. | 7,500 | 50.00–50.99 | ±1.5% ต่อ 1 บาท | 6,500 |
| 12–15 เม.ย. | 8,000 | 50.00–50.99 | ±1.5% ต่อ 1 บาท | 6,500 |

## ราคาน้ำมัน
- แหล่ง: ตารางบางจาก (คัดลอกจากหน้า historical) — **คอลัมน์ที่ 2** หลังวันที่ (~40–50 บาท/ล.)
- เก็บใน `oatside_config.json` → `diesel_price_history` ช่วง 2026-04-01 … 2026-04-30
- วันไม่มีประกาศ: carry-forward จากวันประกาศล่าสุดก่อนหน้า

## พ.ค. 2569 (ที่ลูกค้าเห็นบนเว็บ)
- ดูรายงาน: https://yk-logistics.github.io/transport-rate-calculator/reports/oatside-pg-2026/
- ฐาน **6,500** ที่แถบน้ำมัน **31.00–31.99** บ./ล. ปรับ **+1.5% ต่อ 1 บาท**
- ราคาน้ำมัน: ไฮดีเซล S **คอลัมน์ที่ 5** จากตารางบางจาก (ประมาณ 31–34 บ./ล.)

## สำเนาใน config
- `oatside_config.json` → `_billing_locked_april_2026`
""",
        encoding="utf-8",
    )

    text = BUILD_PATH.read_text(encoding="utf-8")
    if "customer_rate_summary: str | None = None" not in text:
        text = text.replace(
            "    report_end_date: date | None\n",
            "    report_end_date: date | None\n    customer_rate_summary: str | None = None\n",
        )
    if "customer_rate_summary=_parse_optional_str" not in text:
        text = text.replace(
            "    report_end_date = _parse_optional_iso_date(raw.get(\"report_end_date\"))\n",
            "    report_end_date = _parse_optional_iso_date(raw.get(\"report_end_date\"))\n"
            "    customer_rate_summary = _parse_optional_str(raw.get(\"customer_rate_summary\"))\n",
        )
        if "def _parse_optional_str" not in text:
            text = text.replace(
                "def _parse_optional_iso_date",
                "def _parse_optional_str(val: Any) -> str | None:\n"
                "    if val is None:\n"
                "        return None\n"
                "    s = str(val).strip()\n"
                "    return s or None\n\n\n"
                "def _parse_optional_iso_date",
            )
        text = text.replace(
            "        report_end_date=report_end_date,\n",
            "        report_end_date=report_end_date,\n"
            "        customer_rate_summary=customer_rate_summary,\n",
        )
    old_summary = '''def config_rate_summary(cfg: OatsideConfig) -> str:
    """Human-readable summary of rate rules for subtitles/logs."""
    parts = []
    for rule in cfg.trip_rates:'''
    new_summary = '''def config_rate_summary(cfg: OatsideConfig) -> str:
    """Human-readable summary of rate rules for subtitles/logs."""
    if cfg.customer_rate_summary:
        return cfg.customer_rate_summary
    parts = []
    for rule in cfg.trip_rates:'''
    if old_summary in text:
        text = text.replace(old_summary, new_summary)
    BUILD_PATH.write_text(text, encoding="utf-8")

    print("Updated", CONFIG_PATH)
    print("May diesel anchors:", len(may_dates), may_dates)
    print("Wrote", APR_DOC)
    print("Patched", BUILD_PATH.name)


if __name__ == "__main__":
    main()
