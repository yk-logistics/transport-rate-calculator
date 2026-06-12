"""จัด LINE group → Discord category ตามชื่อกลุ่ม (pure function, ไม่แตะเน็ต)

ตรวจตามลำดับ CATEGORY_RULES — keyword ตัวแรกที่เจอใน lower(name) ชนะ
ไม่เข้าข้อใด → DEFAULT_CATEGORY
"""

DEFAULT_CATEGORY = "ลูกค้า-อื่นๆ"

# (category_name, [keywords lowercase]) — ลำดับสำคัญ: DHL ก่อน, ซ่อมก่อนลูกค้า
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("ลูกค้า-DHL", ["dhl", "เรียกรถ"]),  # เรียกรถ = Chevrolet งานของ DHL
    ("ซ่อมบำรุง", ["ซ่อม", "อู่", "อู๋", "ช่าง", "ยาง", "ไทร์", "tire",
                   "isuzu", "ออโต้", "เทคนิค", "การยาง",
                   "p&w", "superpart", "spp"]),
    ("น้ำมัน", ["caltex", "ปตท", "ptt", "น้ำมัน", "เชื้อเพลิง"]),
    ("ภายใน", ["บัญชี", "สำนักงาน", "test", "วาย.เค.ลอจิสติค",
               "หัวลาก", "พขร", "หัวหน้างาน", "ขับรถ"]),
]


def category_for(group_name: str | None) -> str:
    name = (group_name or "").lower()
    for category, keywords in CATEGORY_RULES:
        if any(kw in name for kw in keywords):
            return category
    return DEFAULT_CATEGORY
