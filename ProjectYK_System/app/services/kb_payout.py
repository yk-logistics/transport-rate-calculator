# -*- coding: utf-8 -*-
"""KB payout จากอินวอย CY ใน Google Drive — read-only ไม่แตะ DB/payroll.

ใช้ทั้งหน้า /kb-payout ใน MVP (โอกดเองได้ ไม่ต้องมี AI) และ CLI tools/kb_payout.py.

สูตร CY (โอยืนยัน 1ก.ค.69):
  KB ต่อใบ = Σค่าขนส่ง (ชีท "ค่าขนส่ง" คอลัมน์ J ต่อตู้)
             − (ราคาเสนอในชื่อไฟล์ × จำนวนตู้) − OT (เลขหลัง + ในชื่อไฟล์)
  โอนคืนเจ้าของงาน = KB × 90% (บริษัทเก็บ 10%)
  ใบหัก ณ ที่จ่าย = 3% ของ KB เต็ม (ออกเอกสารอย่างเดียว ไม่ลบจากยอดโอน)
การจับคู่ยอดโอนลูกค้า: CY มักหัก ณ ที่จ่าย 1% เฉพาะส่วนค่าขนส่ง (ไม่หักค่าสำรองจ่าย)
— ยืนยันจากยอดโอนจริง 1ก.ค.69 19,027.98 = CYIV2606-023+026.
"""
from __future__ import annotations

import io
import os
import re
from pathlib import Path

KB_OUR_CUT = 0.10
KB_WHT = 0.03

CY_FOLDER = "1aaiw4o9YJIW0sAqJk2-IoNqwmMWxHoCc"
KB_OWNERS = {  # เจ้าของงานผู้รับ KB (จากดีไซน์ 1ก.ค.)
    "CY": {"owner": "ชาญณรงค์ มาลีแย้ม", "bank": "กสิกร 844-205-5344"},
}

FNAME_RE = re.compile(r"(CYIV\d{4}-\d{3})\s+(.+?)\s+(\d+)(?:\+(\d+))?\.xlsx$", re.I)

_KEY_NAME = "noble-history-446303-e4-c36409a0122c.json"
_APP_DIR = Path(__file__).resolve().parents[1]


def _key_path() -> Path:
    """หา service-account key: env YK_GDRIVE_KEY → โฟลเดอร์แอป (server) → ราก repo (dev)."""
    cand = [Path(p) for p in [os.environ.get("YK_GDRIVE_KEY", "")] if p]
    cand += [_APP_DIR / _KEY_NAME, _APP_DIR.parents[1] / _KEY_NAME]
    for p in cand:
        if p.exists():
            return p
    raise RuntimeError("ไม่พบไฟล์ key เข้า Google Drive (YK_GDRIVE_KEY)")


def _svc():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        str(_key_path()), scopes=["https://www.googleapis.com/auth/drive.readonly"])
    return build("drive", "v3", credentials=creds)


def _list_children(svc, folder_id):
    res = svc.files().list(q=f"'{folder_id}' in parents and trashed=false",
                           fields="files(id,name,mimeType)", pageSize=300,
                           orderBy="name").execute()
    return res.get("files", [])


def _download(svc, fid: str, name: str) -> Path:
    """โหลดไฟล์อินวอย (cache — ไฟล์ออกแล้วไม่ค่อยแก้; ลบโฟลเดอร์ cache = โหลดใหม่)."""
    from googleapiclient.http import MediaIoBaseDownload

    cache = _APP_DIR / "_kb_payout_cache"
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / f"{fid}_{name}"
    if dest.exists():
        return dest
    buf = io.BytesIO()
    dn = MediaIoBaseDownload(buf, svc.files().get_media(fileId=fid))
    done = False
    while not done:
        _, done = dn.next_chunk()
    dest.write_bytes(buf.getvalue())
    return dest


def parse_invoice(path: Path, fname: str) -> dict | None:
    """อ่านอินวอย 1 ใบจากชีท "ค่าขนส่ง" (ต่อตู้) — ไม่ใช่หน้าปะหน้าที่รวมค่าใช้จ่าย."""
    import openpyxl

    m = FNAME_RE.search(fname)
    if not m:
        return None
    inv, customer, quote, ot = m.group(1), m.group(2), float(m.group(3)), float(m.group(4) or 0)

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb["ค่าขนส่ง"] if "ค่าขนส่ง" in wb.sheetnames else wb[wb.sheetnames[-1]]
    qty = 0
    transport = ot_sheet = advances = row_sum = 0.0
    for row in ws.iter_rows(min_row=15, max_row=60):
        vals = {c.coordinate.rstrip("0123456789"): c.value for c in row if c.value is not None}
        if isinstance(vals.get("A"), (int, float)):  # แถวตู้: A = เลขลำดับ
            qty += 1
            transport += float(vals.get("J") or 0)
            ot_sheet += float(vals.get("K") or 0)
            advances += float(vals.get("L") or 0)
            row_sum += float(vals.get("M") or 0)
    wb.close()
    return {
        "inv": inv, "customer": customer.strip(), "quote": quote, "ot": ot,
        "qty": qty, "transport": transport, "ot_sheet": ot_sheet,
        "advances": advances, "grand_total": round(row_sum, 2),
    }


def kb_of(r: dict) -> float:
    return round(r["transport"] - r["quote"] * r["qty"] - r["ot"], 2)


def load_all() -> list[dict]:
    """อินวอย CY ทุกใบจาก Drive (ทุกโฟลเดอร์เดือน) พร้อม KB ต่อใบ."""
    svc = _svc()
    rows = []
    for sub in _list_children(svc, CY_FOLDER):
        if not sub["mimeType"].endswith("folder"):
            continue
        for f in _list_children(svc, sub["id"]):
            if not f["name"].lower().endswith(".xlsx"):
                continue
            r = parse_invoice(_download(svc, f["id"], f["name"]), f["name"])
            if r:
                r["month_folder"] = sub["name"]
                r["kb"] = kb_of(r)
                rows.append(r)
    rows.sort(key=lambda r: r["inv"])
    return rows


RECEIPT_VARIANTS = [
    ("หัก ณ ที่จ่าย 1% เฉพาะค่าขนส่ง", lambda r: r["grand_total"] - round(r["transport"] * 0.01, 2)),
    ("หัก ณ ที่จ่าย 1% ทั้งใบ", lambda r: r["grand_total"] - round(r["grand_total"] * 0.01, 2)),
    ("จ่ายเต็ม ไม่หักภาษี", lambda r: r["grand_total"]),
    ("หัก ณ ที่จ่าย 3% ทั้งใบ", lambda r: r["grand_total"] - round(r["grand_total"] * 0.03, 2)),
]


def subset_match(rows: list[dict], target: float, receipt_fn) -> list[list[dict]]:
    """หาชุดอินวอยที่ยอดรับรวมตรง target เป๊ะระดับสตางค์ (DP บนสตางค์)."""
    t = round(target * 100)
    items = [(r, round(receipt_fn(r) * 100)) for r in rows]
    sums: dict[int, list[tuple]] = {0: [()]}
    for idx, (_r, cents) in enumerate(items):
        if cents <= 0:
            continue
        for s in sorted([s for s in sums if s + cents <= t], reverse=True):
            combos = sums.setdefault(s + cents, [])
            if len(combos) < 20:
                combos.extend(tuple(c) + (idx,) for c in sums[s][:5])
    return [[items[i][0] for i in combo] for combo in sums.get(t, [])]


def match_amount(rows: list[dict], amount: float) -> dict:
    """ลองทุก variant การหักภาษี → คืน {variant, combos:[{invoices, kb_total, payout, wht_cert, receipt_by_inv}]}."""
    for label, fn in RECEIPT_VARIANTS:
        found = subset_match(rows, amount, fn)
        if not found:
            continue
        combos = []
        for combo in found[:5]:
            combo = sorted(combo, key=lambda r: r["inv"])
            kb_total = round(sum(r["kb"] for r in combo), 2)
            combos.append({
                "invoices": combo,
                "receipts": {r["inv"]: fn(r) for r in combo},
                "kb_total": kb_total,
                "payout": round(kb_total * (1 - KB_OUR_CUT), 2),
                "wht_cert": round(kb_total * KB_WHT, 2),
            })
        return {"variant": label, "combos": combos}
    return {"variant": None, "combos": []}
