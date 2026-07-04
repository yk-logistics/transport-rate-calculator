# -*- coding: utf-8 -*-
"""ซ้อมกู้ backup อัตโนมัติ (S5 §5 — "backup ที่ไม่เคยซ้อมกู้ = ไม่มี backup").

รันจากเครื่อง Dev (อ่าน mirror) หรือบน server (อ่าน D:\\YK_BACKUPS) — READ-ONLY:
แตก zip ล่าสุดลงโฟลเดอร์ชั่วคราว → pragma integrity_check ทั้ง 2 DB →
นับแถวตารางหลักเทียบขั้นต่ำ → พิมพ์สรุปพร้อมบรรทัดไว้แปะตารางประวัติใน checklist.
ไม่แตะไฟล์จริงใดๆ ทั้งสิ้น; โฟลเดอร์ทดสอบลบทิ้งตอนจบ (เว้น --keep).

ใช้:  python restore_drill.py                    # หา zip ล่าสุดเอง (mirror → D:)
      python restore_drill.py --zip <path.zip>   # ระบุ zip เอง
      python restore_drill.py --keep             # เก็บโฟลเดอร์แตกไว้ดูต่อ
"""
import argparse
import io
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SEARCH_DIRS = [
    Path(r"C:\Users\guole\YK_BACKUPS_MIRROR"),      # เครื่อง Dev (ชั้น 3)
    Path(r"D:\YK_BACKUPS\daily"),                    # server (ชั้น 1)
    Path(r"D:\YK_BACKUPS"),
]
# ตารางหลัก + จำนวนแถวขั้นต่ำที่ "backup ดีต้องมี" (ต่ำกว่านี้ = ผิดปกติ ให้คนดู)
MIN_ROWS = {"dailyjob": 2000, "fueltxn": 1000, "payrun": 10, "appuser": 1}


def find_latest_zip() -> Path | None:
    zips = []
    for d in SEARCH_DIRS:
        if d.exists():
            zips += list(d.glob("yk_hot_*.zip"))
    return max(zips, key=lambda p: p.stat().st_mtime) if zips else None


def check_db(p: Path, min_rows: dict) -> list[str]:
    """คืน list ปัญหา (ว่าง = ผ่าน) — เปิด read-only."""
    problems = []
    con = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
    try:
        ic = con.execute("pragma integrity_check").fetchone()[0]
        if ic != "ok":
            problems.append(f"integrity_check != ok: {ic[:120]}")
            return problems
        for table, need in min_rows.items():
            try:
                n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except sqlite3.OperationalError:
                problems.append(f"ไม่มีตาราง {table}")
                continue
            if n < need:
                problems.append(f"{table} มี {n} แถว (< ขั้นต่ำ {need})")
            else:
                print(f"    {table}: {n:,} แถว ✓")
    finally:
        con.close()
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", dest="zip_path", default="")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    z = Path(args.zip_path) if args.zip_path else find_latest_zip()
    if not z or not z.exists():
        print("❌ ไม่พบ zip backup — เช็ค mirror/D: หรือระบุ --zip เอง")
        return 2
    age_h = (datetime.now().timestamp() - z.stat().st_mtime) / 3600
    print(f"zip: {z}  ({z.stat().st_size/1e6:.1f} MB, อายุ {age_h:.0f} ชม.)")
    if age_h > 48:
        print("⚠ zip อายุเกิน 2 วัน — เช็คว่า backup รายคืนยังเดินอยู่ไหม")

    tmp = Path(tempfile.mkdtemp(prefix="yk_restore_drill_"))
    ok = True
    try:
        with zipfile.ZipFile(z) as zf:
            zf.extractall(tmp)
        app_db = tmp / "db" / "app.db"
        line_db = tmp / "db" / "line_archive.db"
        for name, p, mins in (("app.db", app_db, MIN_ROWS),
                              ("line_archive.db", line_db, {"line_message": 10000})):
            print(f"\n== {name} ==")
            if not p.exists():
                print("    ❌ ไม่มีในzip")
                ok = False
                continue
            problems = check_db(p, mins)
            if problems:
                ok = False
                for x in problems:
                    print(f"    ❌ {x}")
            else:
                print("    integrity ok ✓")
        n_cfg = len(list((tmp / "config").glob("*"))) if (tmp / "config").exists() else 0
        print(f"\nconfig ใน zip: {n_cfg} ไฟล์")
        if n_cfg == 0:
            print("⚠ ไม่มีโฟลเดอร์ config — เช็ค backup_tier1.py SERVER['extras']")
    finally:
        if args.keep:
            print(f"\n(เก็บโฟลเดอร์แตกไว้ที่ {tmp})")
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    stamp = datetime.now().strftime("%d %b %Y")
    print(f"\n{'✅ ซ้อมกู้ผ่าน' if ok else '❌ ซ้อมกู้ไม่ผ่าน — ดูรายการด้านบน'}")
    print(f"บรรทัดแปะ checklist: | {stamp} | restore_drill.py | "
          f"{'ผ่าน (integrity ok ทั้ง 2 DB + จำนวนแถวเกินขั้นต่ำ)' if ok else 'ไม่ผ่าน — ดู log'} |")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
