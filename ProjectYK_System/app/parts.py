# -*- coding: utf-8 -*-
"""P1: สิทธิ์ละเอียดระดับ "ชิ้นส่วนในหน้า" (part) — ชั้นถัดจาก permissions ระดับเมนู.

- part key ฝังใน template ผ่าน helper `part_visible(request, key)` /
  `part_editable(request, key)` (ลงทะเบียนใน main.py)
- default ตายตัวอยู่ที่ PART_DEFAULTS; โอปรับสดที่ /admin/permissions →
  เขียนตาราง PartPermission (role-level หรือ override รายคน — รายคนชนะ role)
- ระดับ: hide (ไม่เห็น) | view (เห็นอย่างเดียว) | edit (เห็น+แก้)
- cache ในโปรเซส — หน้า admin บันทึกแล้วเรียก invalidate_cache() (uvicorn โปรเซสเดียว)

เพิ่มจุดใหม่: เพิ่ม key ใน PART_DEFAULTS + ครอบ template ด้วย helper
(+ เช็คซ้ำฝั่ง POST ถ้าเป็นจุดแก้เงิน) — หน้า /admin/permissions โชว์เองอัตโนมัติ.
"""
from __future__ import annotations

from typing import Optional

LEVELS = ("hide", "view", "edit")

# part_key -> {"label": คำอธิบายให้โออ่าน, "roles": default ต่อ role}
# role ที่ไม่ระบุ = hide (fail closed)
PART_DEFAULTS: dict[str, dict] = {
    "transfer.edit_account": {
        "label": "หน้าโอนเงิน: ปุ่มแก้ธนาคาร/เลขบัญชีพนักงาน",
        "roles": {"admin": "edit"},
    },
    "daily.money_cols": {
        "label": "เดลี่ grid: คอลัมน์เงิน (ราคาลูกค้า/ค่าเที่ยวคนขับ/ราคากลาง)",
        "roles": {"admin": "edit", "office": "edit", "accountant": "view"},
    },
    "daily.kb_col": {
        "label": "เดลี่ grid: คอลัมน์ KB (ข้อมูลลับ)",
        "roles": {"admin": "edit"},
    },
    "ar.settle": {
        "label": "หน้ารอรับเงิน: ปุ่มติ๊ก 'รับแล้ว'",
        "roles": {"admin": "edit", "accountant": "edit"},
    },
}

_cache: Optional[dict] = None  # {(part_key, "r:"+role | "u:"+username): level}


def invalidate_cache() -> None:
    global _cache
    _cache = None


def _load(session) -> dict:
    global _cache
    if _cache is None:
        from sqlmodel import select
        from models import PartPermission

        _cache = {}
        for row in session.exec(select(PartPermission)).all():
            if row.level not in LEVELS:
                continue
            key = f"u:{row.username}" if row.username else f"r:{row.role}"
            _cache[(row.part_key, key)] = row.level
    return _cache


def part_level(session, role: str, username: str, part_key: str) -> str:
    """ระดับสิทธิ์ของ user ต่อ part: override รายคน > แถว role ใน DB > default ในโค้ด."""
    spec = PART_DEFAULTS.get(part_key)
    if spec is None:
        return "edit" if role == "admin" else "hide"  # key ไม่รู้จัก — fail closed
    data = _load(session)
    for k in (f"u:{username}", f"r:{role}"):
        lv = data.get((part_key, k))
        if lv:
            return lv
    return spec["roles"].get(role, "hide")
