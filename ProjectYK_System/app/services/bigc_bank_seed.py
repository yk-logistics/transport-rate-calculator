"""BIGC เลขบัญชีโอนเดือน — seed เมื่อ Employee.custom_terms ยังว่าง (ตารางยืนยันผู้ใช้เมษายน 2569)

ถ้ากรอก bank_name / bank_account / payment_note ใน custom_terms แล้ว → ใช้ของพนักงานก่อนเสมอ
"""

from __future__ import annotations

from typing import Optional

from services.alias_map import canonical_person_name, normalize_person_name


def _n(raw: str) -> str:
    return normalize_person_name(raw)


# คีย์หลายแบบสำหรับชื่อที่สะกดต่าง (PDF vs master)
# รายการตามตารางผู้ใช้ (ลำดับ 1–9): กดสดใช้ bank_name / #N/A ใช้ payment_note เพื่อไม่ให้ขึ้น "กดเงินสด" ผิดคอลัมน์
BIGC_BANK_SEED_FLAT: dict[str, dict[str, str]] = {
    _n("เกรียงไกร สายแก้ว"): {"bank_name": "กดเงินสด", "bank_account": "", "payment_note": ""},
    _n("เกรียงไกร สำยแก้ว"): {"bank_name": "กดเงินสด", "bank_account": "", "payment_note": ""},
    _n("สมัย ราศรี"): {"bank_name": "กรุงศรี", "bank_account": "610 - 132 - 0079", "payment_note": ""},
    _n("สมัย รำศรี"): {"bank_name": "กรุงศรี", "bank_account": "610 - 132 - 0079", "payment_note": ""},
    _n("ธนวัฒน์ ไชยนอก"): {"bank_name": "กสิกร", "bank_account": "142 - 895 - 7861", "payment_note": ""},
    _n("สมประสงค์ กุมประสิทธิ์"): {"bank_name": "SCB", "bank_account": "380-439-4641", "payment_note": ""},
    _n("เกศศักดิ์ ชาวยศ"): {"bank_name": "กรุงไทย", "bank_account": "496 - 051 - 5384", "payment_note": ""},
    _n("เกศศักดิ์ ชำวยศ"): {"bank_name": "กรุงไทย", "bank_account": "496 - 051 - 5384", "payment_note": ""},
    _n("สมพร โม่งปราณีต"): {"bank_name": "กสิกร", "bank_account": "118 - 836 - 7174", "payment_note": ""},
    _n("สมพร โม่งปรำณีต"): {"bank_name": "กสิกร", "bank_account": "118 - 836 - 7174", "payment_note": ""},
    _n("สมพร BIG-C"): {"bank_name": "กสิกร", "bank_account": "118 - 836 - 7174", "payment_note": ""},
    _n("ณัชพน หอมหวน"): {"bank_name": "กสิกร", "bank_account": "116 - 337 - 9992", "payment_note": ""},
    _n("ณัชพล หอมหวน"): {"bank_name": "กสิกร", "bank_account": "116 - 337 - 9992", "payment_note": ""},
    _n("บุญชอบ พูลสวัสดิ์"): {"bank_name": "", "bank_account": "", "payment_note": "#N/A"},
    _n("อภิรักษ์ บริสุทธิ์"): {"bank_name": "กสิกร", "bank_account": "018 - 837 - 7033", "payment_note": ""},
    _n("พรศักดิ์ เด่นดวง"): {"bank_name": "กดเงินสด", "bank_account": "", "payment_note": ""},
}


def _unique_prefix_seed_match(emp_norm: str) -> Optional[dict[str, str]]:
    """ถ้าในระบบเหลือแค่ชื่อส่วนหน้า — จับคู่ seed เมื่อมีเพียง «ชุดเลขบัญชี» เดียวที่ชื่อใน seed ขึ้นต้นตรง."""
    if not emp_norm or len(emp_norm) < 4:
        return None
    uniq: dict[tuple[str, str, str], dict[str, str]] = {}
    for seed_k, seed_v in BIGC_BANK_SEED_FLAT.items():
        if seed_k.startswith(emp_norm):
            fp = (
                seed_v.get("bank_name") or "",
                seed_v.get("bank_account") or "",
                seed_v.get("payment_note") or "",
            )
            uniq[fp] = seed_v
    if len(uniq) != 1:
        return None
    return dict(next(iter(uniq.values())))


def lookup_bigc_bank(full_name: str) -> Optional[dict[str, str]]:
    """คืนค่า seed dict หรือ None"""
    fn = (full_name or "").strip()
    if not fn:
        return None
    c = canonical_person_name(fn, "BIGC")
    k1 = normalize_person_name(c)
    if k1 in BIGC_BANK_SEED_FLAT:
        return dict(BIGC_BANK_SEED_FLAT[k1])
    k2 = normalize_person_name(fn)
    if k2 in BIGC_BANK_SEED_FLAT:
        return dict(BIGC_BANK_SEED_FLAT[k2])
    hit = _unique_prefix_seed_match(k1)
    if hit:
        return hit
    hit = _unique_prefix_seed_match(k2)
    if hit:
        return hit
    return None
