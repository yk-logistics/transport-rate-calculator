"""KB (ใต้โต๊ะ) rule helpers — default ต่อ status_code + คำเตือนกันลืม.

10%/WHT 3% ไม่เก็บเป็น field — คำนวณสดจาก config คงที่ตอนทำรายงาน.
"""
from sqlmodel import Session, select

from models import KbRule

KB_OUR_CUT = 0.10  # ส่วนที่เราเก็บไว้จาก KB
KB_WHT = 0.03      # หัก ณ ที่จ่ายที่เราออกให้


def kb_default_for_status(session: Session, status_code: str) -> float:
    """ค่า KB ตั้งต้นต่อแถวตาม rule ของ status_code; ไม่มี rule → 0.0."""
    rule = session.exec(
        select(KbRule).where(KbRule.status_code == status_code)
    ).first()
    return rule.default_kb if rule else 0.0


def kb_warning_for_row(session: Session, status_code: str, kb_amount: float) -> bool:
    """True เมื่อ rule บังคับ KB (required) แต่แถวนี้ kb_amount == 0 → เตือนกันลืม."""
    rule = session.exec(
        select(KbRule).where(KbRule.status_code == status_code)
    ).first()
    return bool(rule and rule.required and (kb_amount or 0.0) == 0.0)
