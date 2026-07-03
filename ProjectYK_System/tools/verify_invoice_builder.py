# -*- coding: utf-8 -*-
"""ตรวจเกณฑ์ผ่าน C2: ใบที่ระบบออก = ไฟล์จริงที่ทีมทำมือ ทุกตัวเลข (read-only).

วิธีรัน (จากราก repo):
    ProjectYK_System\\app\\.venv\\Scripts\\python.exe ProjectYK_System\\tools\\verify_invoice_builder.py ^
        --db <app.db สำเนา server> --real <ไฟล์ใบจริง.xlsx> --inv KTIV2606-017 --series KMMT

หลัก: ดึงแถวเดลี่ของใบนั้นจาก DB → เติมช่องที่ผู้ใช้ต้องกรอก (ป้าย/ค่าทดรองจ่าย/
ค่าธรรมเนียม) จาก "ไฟล์จริง" (จำลองสิ่งที่ทีมพิมพ์) → build → เทียบช่องต่อช่อง:
ตัวเลขที่มาจาก DB (ราคา/ตู้/ไซส์/ทะเบียน/วันที่) ต้องตรงไฟล์จริงเป๊ะ ไม่ตรง = FAIL.
"""
from __future__ import annotations

import argparse
import io
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from services.invoice_builder import REGISTRY, build_invoice  # noqa: E402


def norm(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, float) and v == int(v):
        return int(v)
    if isinstance(v, str):
        return v.strip()
    return v


def main() -> int:
    import openpyxl

    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--real", required=True)
    ap.add_argument("--inv", required=True)
    ap.add_argument("--series", required=True, choices=sorted(REGISTRY))
    args = ap.parse_args()

    cfg = REGISTRY[args.series]
    charge_cols = {c["key"]: c["col"] for c in cfg.charges}
    read_cols = dict(cfg.cols) | charge_cols

    real = openpyxl.load_workbook(args.real, data_only=True)
    rw = real[cfg.detail_sheet]

    # แถวจริงในไฟล์ (มีเลขลำดับใน A)
    real_rows = []
    for r in range(cfg.row_start, cfg.row_end + 1):
        if rw[f"A{r}"].value is None:
            continue
        rec = {k: norm(rw[f"{col}{r}"].value) for k, col in read_cols.items()}
        # ไฟล์จริงบางใบพิมพ์เลขลำดับค้างไว้ล่วงหน้า — แถวไม่มีตู้และไม่มีราคา = แถวเปล่า
        if rec.get("cntr") in (None, "") and not rec.get("price"):
            continue
        rec["_r"] = r
        real_rows.append(rec)
    inv_date = norm(rw[cfg.date_cell].value)

    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    db_rows = [dict(x) for x in con.execute(
        "SELECT * FROM dailyjob WHERE invoice_no=? ORDER BY work_date, id", (args.inv,))]
    if len(db_rows) != len(real_rows):
        print(f"FAIL {args.inv}: จำนวนแถว DB={len(db_rows)} ไฟล์จริง={len(real_rows)}")
        return 1

    # จับคู่แถวด้วยเลขตู้ (ลำดับในไฟล์อาจไม่ตรงลำดับ DB)
    by_cntr = {r["container_no"]: r for r in db_rows}
    rows, fails = [], []
    for fr in real_rows:
        j = by_cntr.get(str(fr["cntr"]))
        if j is None:
            fails.append(f"ตู้ {fr['cntr']} ไม่มีใน DB")
            continue
        # ช่องที่มาจาก DB ต้องตรงไฟล์จริง
        checks = {
            "ราคา": (float(j["revenue_customer"]), float(fr["price"] or 0)),
            "ไซส์": (str(j["container_size"]), str(fr["size"])),
            "วันที่": (j["work_date"], str(fr["date"])),
        }
        if "plate" in cfg.cols:
            checks["ทะเบียน"] = (str(j["plate_no_raw"]), str(fr["plate"]))
        # job/BL เทียบเฉพาะเมื่อ DB มีค่า — CY/CJ/NHL ไม่คีย์ในเดลี่ (ช่องกรอกใน UI)
        job_db = str(j[cfg.job_field] or "").strip()
        if job_db:
            checks["job/BL"] = (job_db, str(fr.get("job") or "").strip())
        for name, (db_v, f_v) in checks.items():
            if str(db_v) != str(f_v):
                fails.append(f"{args.inv} ตู้ {fr['cntr']} {name}: DB={db_v!r} ไฟล์={f_v!r}")
        row = {
            "route": fr.get("route") or "", "cntr": fr["cntr"],
            "size": fr["size"], "plate": fr.get("plate") or "",
            "cust": fr.get("cust") or "", "job": fr.get("job") or "",
            "date": date.fromisoformat(j["work_date"]),
            "price": j["revenue_customer"], "advance": 0.0, "_r": fr["_r"],
        }
        for k in charge_cols:
            row[k] = float(fr.get(k) or 0)
        rows.append(row)

    # ค่าทดรองจ่ายชีทแยก (KMMT): เอาจากไฟล์จริง (สิ่งที่ผู้ใช้กรอก)
    if cfg.advance_sheet:
        ra = real[cfg.advance_sheet]
        price_col = cfg.cols["price"]
        for row in rows:
            row["advance"] = float(norm(ra[f"{price_col}{row['_r']}"].value) or 0)

    if fails:
        print(f"FAIL {args.inv} (DB ไม่ตรงไฟล์จริง):")
        for f in fails:
            print(" -", f)
        return 1

    built = build_invoice(cfg, args.inv, inv_date, rows)
    gen = openpyxl.load_workbook(io.BytesIO(built))
    gw = gen[cfg.detail_sheet]

    diffs = []
    if norm(gw[cfg.inv_cell].value) != norm(rw[cfg.inv_cell].value):
        diffs.append(f"{cfg.inv_cell}: {gw[cfg.inv_cell].value!r} != {rw[cfg.inv_cell].value!r}")
    if norm(gw[cfg.date_cell].value) != inv_date:
        diffs.append(f"{cfg.date_cell}: {gw[cfg.date_cell].value!r} != {inv_date!r}")
    for i, fr in enumerate(real_rows):
        gr = cfg.row_start + i  # generated เรียงตามไฟล์จริง
        for k, col in read_cols.items():
            gv, fv = norm(gw[f"{col}{gr}"].value), fr[k]
            if k == "price" or k in charge_cols:
                gv, fv = float(gv or 0), float(fv or 0)
            if (gv or "") != (fv or "") and str(gv) != str(fv):
                diffs.append(f"ค่าขนส่ง {col}{gr} ({k}): gen={gv!r} real={fv!r}")
    total_gen = sum(
        float(r["price"]) + sum(float(r.get(k) or 0) for k in charge_cols)
        for r in rows)
    total_real = float(norm(rw[cfg.total_cell].value) or 0)
    if abs(total_gen - total_real) > 0.005:
        diffs.append(f"ยอดรวม {cfg.total_cell}: gen={total_gen} real={total_real}")
    if cfg.advance_sheet:
        ga, ra = gen[cfg.advance_sheet], real[cfg.advance_sheet]
        price_col = cfg.cols["price"]
        for i, row in enumerate(rows):
            gr = cfg.row_start + i
            gv = float(norm(ga[f"{price_col}{gr}"].value) or 0)
            fv = float(norm(ra[f"{price_col}{row['_r']}"].value) or 0)
            if abs(gv - fv) > 0.005:
                diffs.append(f"ทดรองจ่าย {price_col}{gr}: gen={gv} real={fv}")
        adv_gen = sum(r["advance"] for r in rows)
        adv_real = float(norm(ra[f"{price_col}{cfg.advance_row_end + 1}"].value) or 0)
        if abs(adv_gen - adv_real) > 0.005:
            diffs.append(f"ยอดทดรองจ่ายรวม: gen={adv_gen} real={adv_real}")

    if diffs:
        print(f"FAIL {args.inv}:")
        for d in diffs:
            print(" -", d)
        return 1
    print(f"PASS {args.inv} ({args.series}): {len(rows)} ตู้ ราคาจาก DB ตรงไฟล์จริงทุกช่อง; "
          f"ยอดรวม {total_gen:,.2f} ตรง; ใบ generate ช่องตรงไฟล์จริงครบ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
