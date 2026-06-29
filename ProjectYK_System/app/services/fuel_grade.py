"""เดาเกรดน้ำมัน B7/B20 จากราคา/ลิตร.

หลัก: ในการเติมครั้งเดียวรถคันเดียว B20 ถูกกว่า B7 ชัด (~6฿/L) →
เทียบราคา "ภายในกลุ่มเดียวกัน" (relative) เชื่อถือได้กว่าเลขบาทตายตัว
เพราะราคาน้ำมันผันผวนรายวัน. เลข absolute ใช้เป็น fallback ตอนแยกไม่ได้.
fuel_grade เป็นแค่ป้าย — ไม่เข้าไปในสูตรเงินใดๆ.
"""
from __future__ import annotations

B20_MAX_HINT = 38.0   # ราคา <= นี้ เดาเป็น B20 (fallback หยาบ)
GRADE_GAP_MIN = 3.0   # ส่วนต่างราคาในกลุ่มที่ถือว่า "คนละเกรดชัด"


def guess_grade_from_price(price_per_liter: float) -> str:
    if not price_per_liter or price_per_liter <= 0:
        return ""
    return "B20" if price_per_liter <= B20_MAX_HINT else "B7"


def assign_grades_for_group(prices: list[float]) -> list[str]:
    valid = [p for p in prices if p and p > 0]
    if len(valid) >= 2 and (max(valid) - min(valid)) >= GRADE_GAP_MIN:
        mid = (min(valid) + max(valid)) / 2.0
        out = []
        for p in prices:
            if not p or p <= 0:
                out.append("")
            elif p <= mid:
                out.append("B20")
            else:
                out.append("B7")
        return out
    return [guess_grade_from_price(p) for p in prices]
