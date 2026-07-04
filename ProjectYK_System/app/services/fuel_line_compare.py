# -*- coding: utf-8 -*-
"""F4 (ไม่ใช้ OCR): เทียบ "ข้อความแจ้งเติม" ในกลุ่มไลน์ปั๊ม ↔ FuelTxn ในระบบ.

ข้อค้นพบ 4ก.ค.: กลุ่มปั๊มโพสต์ข้อความแจ้งเติมมีโครงสร้างอยู่แล้ว เช่น
  "71-8967 นายณัฐวุฒิ เติมดีเซล [20L]+B20 [80L] แจ้งเติมCaltex ศรีไทย"
  "71-0560 นายยา ปตท. เติมดีเซล (20ลิตร) เติมดีเซลB20 (เต็มถัง)"
→ ดึง ทะเบียน + ลิตรต่อเกรด จาก text ตรง ๆ ไม่ต้อง OCR รูปสลิป.

รายงานอย่างเดียว (สเปค F4): ไม่แก้เงิน ไม่เขียน DB ใด ๆ.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime, timedelta

from services import line_archive as la

PLATE_RE = re.compile(r"\b(\d{2,3})\s?-\s?(\d{4})\b")
# ลิตรต่อเกรด: "ดีเซล [20L]" / "ดีเซล (20ลิตร)" / "B20 [80L]" / "B20 (เต็มถัง)"
B20_RE = re.compile(r"B\s?20\D{0,12}?(\d{1,3})\s*(?:L\b|ลิตร)", re.IGNORECASE)
B7_RE = re.compile(r"(?:ดีเซล|B\s?7)(?!\s?20)\D{0,12}?(\d{1,3})\s*(?:L\b|ลิตร)", re.IGNORECASE)
FULL_RE = re.compile(r"เต็มถัง")
LITER_TOL = 5.0     # ลิตรต่างกันได้ ±5 (ตามสเปคเดิม ยอด±5)


def parse_fill_text(text: str) -> dict | None:
    """ข้อความ 1 อัน → คำสั่งเติม {plate, b7, b20, full_tank} — ไม่ใช่คำสั่งเติม = None."""
    t = text or ""
    if "เติม" not in t:
        return None
    m = PLATE_RE.search(t)
    if not m:
        return None
    b7 = sum(int(x) for x in B7_RE.findall(t)) or 0
    b20 = sum(int(x) for x in B20_RE.findall(t)) or 0
    full = bool(FULL_RE.search(t))
    if not (b7 or b20 or full):
        return None
    return {"plate": f"{m.group(1)}-{m.group(2)}", "b7": b7, "b20": b20,
            "full_tank": full}


def fill_orders(group_ids: list[str], days: int = 21) -> list[dict]:
    """ข้อความแจ้งเติมจากกลุ่มปั๊ม (ล่าสุดก่อน) — dedupe โพสต์ซ้ำ (วัน+ทะเบียน+ลิตรเดิม)."""
    if not group_ids:
        return []
    p = la.db_path()
    if p is None:
        raise FileNotFoundError("ไม่พบคลังแชทบนเครื่องนี้ (line_archive.db)")
    since = (date.today() - timedelta(days=days)).isoformat()
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        marks = ",".join("?" * len(group_ids))
        rows = con.execute(f"""
            SELECT m.id, m.group_id, m.sent_at, m.text, g.name AS group_name
            FROM line_message m LEFT JOIN line_group g ON g.group_id = m.group_id
            WHERE m.group_id IN ({marks}) AND m.msg_type = 'text'
              AND substr(m.sent_at, 1, 10) >= ?
            ORDER BY m.sent_at DESC""", (*group_ids, since)).fetchall()
    finally:
        con.close()
    out, seen = [], set()
    for r in rows:
        o = parse_fill_text(r["text"])
        if o is None:
            continue
        try:
            sent = datetime.fromisoformat(str(r["sent_at"]).replace("T", " ")[:16])
        except ValueError:
            continue
        key = (sent.date(), o["plate"], o["b7"], o["b20"], o["full_tank"])
        if key in seen:
            continue
        seen.add(key)
        o.update({"msg_id": r["id"], "date": sent.date(),
                  "sent_at": str(r["sent_at"])[:16],
                  "group_name": r["group_name"] or "",
                  "text": (r["text"] or "")[:160]})
        out.append(o)
    return out


def compare(orders: list[dict], txns: list,
            plate_site: dict[str, str] | None = None,
            site_fuel_max: dict[str, date] | None = None) -> dict:
    """จับคู่คำสั่งเติม ↔ FuelTxn (ทะเบียนตรง + วัน ±1 + ลิตร ±5 ต่อเกรด/เต็มถัง=ไม่เช็คลิตร).

    txns: FuelTxn rows (liter>0 เท่านั้น — ยอดติดลบ/คืนน้ำมันไม่ร่วมจับคู่).
    คืน {matched, line_only, awaiting_import, sys_only, fuel_max_date}
    — คำสั่งเติมที่ใหม่กว่าข้อมูลน้ำมัน "ของไซท์ตัวเอง" = "รอ import" ไม่ใช่ตกหล่น
    (วัดจริง 4ก.ค.: import ตามหลังไม่เท่ากันต่อไซท์ — LCB ถึง 15 มิ.ย. แต่ AYU ถึง 25 มิ.ย.
    ใช้ max รวมจะธง LCB ผิด 100+ รายการ); ไซท์ของทะเบียนดูจาก plate_site (Vehicle master).
    """
    plate_site = plate_site or {}
    site_fuel_max = site_fuel_max or {}
    fuel_max = max((t.txn_date for t in txns), default=None)

    def fresh_until(plate: str) -> date | None:
        site = plate_site.get(plate, "")
        return site_fuel_max.get(site, fuel_max)
    # index: (plate, date) -> [txn]
    by_pd: dict[tuple, list] = {}
    for t in txns:
        if (t.liter or 0) <= 0:
            continue
        by_pd.setdefault(((t.plate_no_raw or "").strip(), t.txn_date), []).append(t)

    used: set[int] = set()
    matched, line_only, awaiting = [], [], []
    for o in orders:
        cands = []
        for dd in (0, 1, -1):
            cands += [t for t in by_pd.get((o["plate"], o["date"] + timedelta(days=dd)), [])
                      if t.id not in used]
        # เกรดในระบบ: B7 มัก 20L, B20 ยอดใหญ่ — จับจากลิตรที่แจ้ง
        want = [x for x in (o["b7"], o["b20"]) if x]
        got = []
        for w in want:
            hit = next((t for t in cands
                        if t.id not in used and abs((t.liter or 0) - w) <= LITER_TOL), None)
            if hit is not None:
                used.add(hit.id)
                got.append(hit)
        if o["full_tank"]:
            hit = next((t for t in cands if t.id not in used and (t.liter or 0) > 30), None)
            if hit is not None:
                used.add(hit.id)
                got.append(hit)
        need = len(want) + (1 if o["full_tank"] else 0)
        fresh = fresh_until(o["plate"])
        if got and len(got) >= need:
            matched.append({"order": o, "txns": got})
        elif fresh is None or o["date"] > fresh - timedelta(days=1):
            # กันชนขอบ 1 วันให้เท่าหน้าต่างจับคู่ ±1 — เติมวันสุดท้ายของ import
            # อาจลงบิลวันถัดไปที่ยังไม่เข้า อย่าเพิ่งธงจนข้อมูลรอบหน้ามา
            awaiting.append(o)          # น้ำมันไซท์นี้ยัง import ไม่ถึงวันนั้น
        elif got:
            matched.append({"order": o, "txns": got, "partial": True})
        else:
            line_only.append(o)

    order_dates = {o["date"] for o in orders}
    arch_min = min(order_dates) if order_dates else None
    sys_only = []
    if arch_min is not None:
        order_pd = {(o["plate"], o["date"]) for o in orders}
        for t in txns:
            if (t.liter or 0) <= 0 or t.id in used or t.txn_date < arch_min:
                continue
            plate = (t.plate_no_raw or "").strip()
            if any((plate, t.txn_date + timedelta(days=dd)) in order_pd
                   for dd in (0, 1, -1)):
                continue
            sys_only.append(t)
    return {"matched": matched, "line_only": line_only,
            "awaiting_import": awaiting, "sys_only": sys_only,
            "fuel_max_date": fuel_max}
