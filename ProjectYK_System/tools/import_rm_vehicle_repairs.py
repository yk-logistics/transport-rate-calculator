# -*- coding: utf-8 -*-
"""ดึง "ตารางซ่อมรายคัน" จาก RM History Google Sheets (สด) → MaintRecord/MaintPart.

    python ProjectYK_System/tools/import_rm_vehicle_repairs.py --file lcb            # dry-run
    python ProjectYK_System/tools/import_rm_vehicle_repairs.py --file lcb --apply
    python ProjectYK_System/tools/import_rm_vehicle_repairs.py --file lcb --rollback --yes

**ต่างจาก `tools/import_rm_history.py` (เม.ย. 2026)** ซึ่งอ่านไฟล์ .xlsx สำเนา และดึงเฉพาะ
แท็บ `บันทึกการซ่อมหัวลาก` + `Stock` (ได้ MaintRecord 146 แถว) — ตัวนี้ดึง **ตารางซ่อมในแท็บ
รายคัน** ทั้ง 126 แท็บ (~9,300 บิล) จากชีทสด

ตรวจทาน 2 ชั้น (สเปคข้อ 10 — แก้ 10 ก.ค. หลังเจอว่ายอดบนชีทเชื่อไม่ได้):
 1) **เทียบทีละบรรทัดกับสูตรของชีทเอง** — ทุกเซลล์ "ราคาสุทธิ" คือ `=(G−H)+I` ฉะนั้น
    ค่าที่เราคำนวณ (รวม−ส่วนลด+VAT) ต้องตรงกับตัวเลขในช่องนั้น ±0.01 ทุกบรรทัด **ต้องเป็น 0 ที่ไม่ตรง**
 2) ยอดสรุปบนหน้าชีท (`=SUBTOTAL(9, J23:J205)`) **ใช้เป็น ground truth ไม่ได้** เพราะ
    (ก) ล็อกช่วงแถวไว้ตายตัว ทีมเพิ่มแถวลงไปโดยไม่ขยายสูตร
    (ข) SUBTOTAL ไม่นับแถวที่ถูกซ่อนด้วยฟิลเตอร์
    → พิมพ์ให้เห็นว่าค่าซ่อมจริงสูงกว่าที่ทีมเห็นเท่าไหร่ (รายงาน ไม่ใช่เกณฑ์ผ่าน)
"""
import argparse
import re
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))

import gspread                                    # noqa: E402
from sqlmodel import Session                      # noqa: E402

from db_config import engine                      # noqa: E402
from services import rm_history as rm             # noqa: E402
from services import rm_history_import as rmi     # noqa: E402

def _find_key_file() -> Path:
    """service account key: dev = รากรีโป, server = YK_MVP\\app\\ (secret #7)."""
    import os

    env = os.getenv("YK_GSHEET_KEY", "").strip()
    if env and Path(env).exists():
        return Path(env)
    for base in (Path(__file__).resolve().parents[2], APP):
        hit = next(base.glob("noble-history-*.json"), None)
        if hit:
            return hit
    raise FileNotFoundError("ไม่พบ noble-history-*.json (ตั้ง env YK_GSHEET_KEY ได้)")


KEY_FILE = _find_key_file()
_SUBTOTAL_RE = re.compile(r"SUBTOTAL\(\s*9\s*,\s*[A-Z]+(\d+)\s*:\s*[A-Z]+(\d+)\s*\)")


def fetch(sheet_id: str) -> tuple[dict, dict]:
    """คืน (ค่าในเซลล์, สูตร) — 2 API call ต่อไฟล์ (โควต้า 60 reads/min)."""
    sh = gspread.service_account(filename=str(KEY_FILE)).open_by_key(sheet_id)
    tabs = [w.title for w in sh.worksheets()]
    vals = sh.values_batch_get([f"'{t}'!A1:K600" for t in tabs])["valueRanges"]
    forms = sh.values_batch_get([f"'{t}'!A1:K30" for t in tabs],
                                params={"valueRenderOption": "FORMULA"})["valueRanges"]
    return ({t: v.get("values", []) for t, v in zip(tabs, vals)},
            {t: f.get("values", []) for t, f in zip(tabs, forms)})


def sheet_checkpoint(values: list, formulas: list) -> tuple[float, float, int] | None:
    """หา SUBTOTAL ที่อยู่ขวาสุด (= คอลัมน์ราคาสุทธิ) → (ยอดที่ชีทโชว์, ยอดที่เราบวกช่วงเดียวกัน, คอลัมน์)."""
    best = None
    for r_i, frow in enumerate(formulas):
        for c_i, cell in enumerate(frow):
            m = _SUBTOTAL_RE.search(str(cell))
            if m and (best is None or c_i > best[0]):
                best = (c_i, r_i, int(m.group(1)), int(m.group(2)))
    if best is None:
        return None
    c_i, r_i, lo, hi = best
    row = values[r_i] if len(values) > r_i else []
    shown = rm._num(row[c_i]) if len(row) > c_i else 0.0
    ours = sum(rm._num(r[c_i]) for r in values[lo - 1:hi] if len(r) > c_i)
    return shown, round(ours, 2), c_i


def run(file_slug: str, apply: bool, create_vehicles: bool = False) -> None:
    sheet_id = rmi.SHEETS[file_slug]
    data, formulas = fetch(sheet_id)

    total = {"bills": 0, "lines": 0, "skipped_dup": 0, "skipped_tab": 0, "blank_net_lines": 0}
    blank_baht = 0.0
    vendors: list[str] = []
    new_vehicles: list[str] = []
    issues: list[dict] = []
    skipped_tabs: list[str] = []
    checks: list[tuple] = []
    line_bad: list[tuple] = []
    line_checked = 0

    with Session(engine) as s:
        for tab, values in data.items():
            parsed = rm.parse_tab(tab, values)
            st = rmi.import_tab(s, file_slug, sheet_id, tab, parsed, dry_run=not apply,
                                create_vehicles=create_vehicles)
            for k in total:
                total[k] += st[k]
            blank_baht = round(blank_baht + st["blank_net_baht"], 2)
            for v in st["new_vendors"]:
                if v not in vendors:
                    vendors.append(v)
            new_vehicles += st["new_vehicles"]
            issues += [{"tab": tab, **i} for i in parsed.issues]
            if st["skipped_tab"]:
                skipped_tabs.append(tab)
                continue
            # ชั้น 1: เทียบทีละบรรทัดกับช่อง "ราคาสุทธิ" ของชีท (ซึ่งเป็นสูตร (G−H)+I)
            for b in parsed.bills:
                for l in b.lines:
                    calc = round(l["total"] - l["discount"] + l["vat"], 2)
                    if l["net"] > 0 and abs(calc - l["net"]) > 0.01:
                        line_bad.append((tab, b.sheet_row, l["name"][:24], calc, l["net"]))
                    line_checked += 1
            cp = sheet_checkpoint(values, formulas.get(tab, []))
            col = cp[2] if cp else 9
            true_net = round(sum(rm._num(r[col]) for r in values[parsed.header_row:]
                                 if len(r) > col), 2)
            checks.append((tab, cp, true_net, st["system_net"]))

    print(f"\n=== {file_slug} ({'APPLY' if apply else 'DRY-RUN'}) ===")
    print(f"บิล {total['bills']} · บรรทัด {total['lines']} · ซ้ำ(ข้าม) {total['skipped_dup']} · "
          f"แท็บที่ข้าม {total['skipped_tab']}")
    print(f"บรรทัดที่ชีทไม่กรอกช่องสุทธิ (โอสั่งให้นับ): {total['blank_net_lines']} บรรทัด "
          f"= {blank_baht:,.2f} บาท")
    if new_vehicles:
        print(f"\nรถที่จะถูกสร้างใหม่ (status=sold — ไม่นับเป็นกำลังรถ) {len(new_vehicles)} คัน:"
              f"\n  {', '.join(new_vehicles)}")
    if skipped_tabs:
        print(f"\nแท็บที่ข้าม (ไม่ใช่ทะเบียนรถ): {', '.join(skipped_tabs)}")
    if vendors:
        print(f"\nร้านใหม่ที่จะถูกสร้าง ({len(vendors)}): {', '.join(vendors[:25])}"
              + (" ..." if len(vendors) > 25 else ""))
    if issues:
        print(f"\nแถวที่ข้าม ({len(issues)}):")
        for i in issues[:20]:
            print(f"  {i['tab']}!แถว{i['row']}: {i['reason']}")
        if len(issues) > 20:
            print(f"  ... อีก {len(issues) - 20} รายการ")

    print("\n--- ชั้น 1: เทียบทีละบรรทัดกับสูตรของชีทเอง (ราคาสุทธิ = รวม − ส่วนลด + VAT) ---")
    print(f"  ตรวจ {line_checked:,} บรรทัด · ไม่ตรง {len(line_bad)} บรรทัด"
          + ("   ✓ ผ่าน" if not line_bad else "   ✗ ไม่ผ่าน — ห้าม --apply"))
    for tab, row, name, calc, net in line_bad[:10]:
        print(f"    {tab}!แถว{row} {name!r} เราคำนวณ {calc:,.2f}  ชีท {net:,.2f}")

    print("\n--- ชั้น 2 (รายงาน): ค่าซ่อมจริง vs ยอดบนชีท (สูตรล็อกช่วง + ไม่นับแถวที่ซ่อน) ---")
    hidden = 0.0
    rows = sorted(checks, key=lambda c: -(c[2] - (c[1][0] if c[1] else 0.0)))
    for tab, cp, true_net, _sys in rows:
        shown = cp[0] if cp else 0.0
        gap = round(true_net - shown, 2)
        hidden += gap
        if gap > 1000:
            print(f"  {tab:<20} ชีทโชว์ {shown:>13,.2f}   จริง {true_net:>13,.2f}   "
                  f"มองไม่เห็น {gap:>13,.2f}")
    print(f"\n  ค่าซ่อมที่ยอดบนชีทมองไม่เห็นรวม ≈ {hidden:,.2f} บาท")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, choices=[*rmi.SHEETS, "all"])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--create-vehicles", action="store_true",
                    help="สร้างรถเก่าที่ไม่มีในระบบเป็น status=sold")
    a = ap.parse_args()

    slugs = list(rmi.SHEETS) if a.file == "all" else [a.file]
    if a.rollback:
        with Session(engine) as s:
            for slug in slugs:
                n = rmi.rollback_file(s, slug, dry_run=True)
                print(f"{slug}: จะลบ {n} บิล (พร้อมบรรทัดลูก)")
                if n and (a.yes or input("พิมพ์ 'yes' เพื่อลบจริง: ") == "yes"):
                    print(f"  ลบแล้ว {rmi.rollback_file(s, slug, dry_run=False)} บิล")
        return
    for slug in slugs:
        run(slug, apply=a.apply, create_vehicles=a.create_vehicles)


if __name__ == "__main__":
    main()
