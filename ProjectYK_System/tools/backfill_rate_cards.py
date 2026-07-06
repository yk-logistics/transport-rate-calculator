# -*- coding: utf-8 -*-
"""D1: backfill RateCard จากแถวเดลี่ที่มีราคา/ค่าเที่ยว/ลิตรอยู่แล้วในประวัติ.

ทำไมต้องมี: auto-learn (rate_record_from_daily) เกิด 4 ก.ค. 2026 — แถวที่ import
มาก่อนหน้านั้นไม่เคยถูกเรียน → คลังเรทว่างสำหรับ BIGC/AYU ทำหน้า /billing/fill-prices
ไม่มีอะไรให้กดรับ. สคริปต์นี้ replay ตรรกะเรียนเดิมกับทุกแถว 'job' ที่มีค่า
(เรียงตามวันทำงาน = ราคาเดินตาม "ล่าสุดชนะ" เหมือนแอปเรียนเอง). Idempotent.

วิธีใช้ (จาก app dir — dev หรือ scp ไปวางบน server แล้วรันตรงนั้น):
    python backfill_rate_cards.py            # dry-run: นับอย่างเดียว ไม่เขียน
    python backfill_rate_cards.py --apply    # เขียนจริง + จด id การ์ดใหม่ลงไฟล์ undo
undo: ลบ RateCard ตาม id ใน _backfill_rate_cards_undo.json (การ์ดเดิมไม่โดนลบ
แต่ use_count/มูลค่า auto อาจถูกอัปเดต — ดู notes ต่อใบ)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def backfill(session, dry_run: bool = True) -> dict:
    """Replay auto-learn over historic priced job rows. ส่ง session สดเข้ามา
    (dry-run จะ rollback ทิ้งทั้ง session)."""
    import main as appmod
    from sqlmodel import select
    from models import DailyJob, RateCard

    before_ids = {c.id for c in session.exec(select(RateCard)).all()}
    learned = 0
    for j in session.exec(select(DailyJob).order_by(
            DailyJob.work_date, DailyJob.id)).all():
        if appmod._daily_row_kind(j) != "job":
            continue
        if not ((j.revenue_customer or 0) > 0 or (j.trip_fee_driver or 0) > 0
                or (j.fuel_liter or 0) > 0):
            continue
        appmod.rate_record_from_daily(session, j)
        learned += 1
    if dry_run:
        session.rollback()
        return {"learned_from": learned, "new_card_ids": []}
    session.commit()
    new_ids = sorted(c.id for c in session.exec(select(RateCard)).all()
                     if c.id not in before_ids)
    return {"learned_from": learned, "new_card_ids": new_ids}


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    for cand in (here, here.parent / "app", here.parents[1] / "app"):
        if (cand / "main.py").exists():
            sys.path.insert(0, str(cand))
            os.chdir(cand)
            break
    else:
        sys.exit("หา app dir (main.py) ไม่เจอ — วางสคริปต์ใน app dir หรือ tools/ ข้าง app/")

    from sqlmodel import Session
    from db_config import engine

    apply_mode = "--apply" in sys.argv
    with Session(engine) as s:
        result = backfill(s, dry_run=not apply_mode)
    result["mode"] = "APPLY" if apply_mode else "DRY-RUN"
    if apply_mode and result["new_card_ids"]:
        undo = Path("_backfill_rate_cards_undo.json")
        undo.write_text(json.dumps(result["new_card_ids"]), encoding="utf-8")
        result["undo_file"] = str(undo.resolve())
    out = dict(result)
    out["new_cards"] = len(out.pop("new_card_ids"))
    print(json.dumps(out, ensure_ascii=False, indent=1))
