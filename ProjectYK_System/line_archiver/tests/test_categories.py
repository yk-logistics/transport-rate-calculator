from categories import category_for

# กลุ่มจริง 45 กลุ่ม → category ที่คาด (โอยืนยัน 2026-06-12)
REAL_GROUPS = {
    "CJ / YK": "ลูกค้า-อื่นๆ",
    "CY & YK": "ลูกค้า-อื่นๆ",
    "Caltex เพิ่มทรัพย์ข้างศรีไทย": "น้ำมัน",
    "DHL Carrier & YK": "ลูกค้า-DHL",
    "DHL-Y.K. : Continental RY-BN": "ลูกค้า-DHL",
    "Fleet YK": "ลูกค้า-อื่นๆ",
    "Isuzu & YK ซ่อมรถใหญ่": "ซ่อมบำรุง",
    "Joe Y.K., ช่างพีท บางปะอิน, O": "ซ่อมบำรุง",
    "KAO MIST&YK": "ลูกค้า-อื่นๆ",
    "KLND & YK": "ลูกค้า-อื่นๆ",
    "NHL & YK Driver": "ลูกค้า-อื่นๆ",
    "Nippon อมตะ & YK": "ลูกค้า-อื่นๆ",
    "Nippon อยุธยา & YK ": "ลูกค้า-อื่นๆ",
    "PX19 x YK": "ลูกค้า-อื่นๆ",
    "SUB YK & DHL BPD": "ลูกค้า-DHL",
    "SUB:Y.K & NHL": "ลูกค้า-อื่นๆ",
    "Test BOT": "ภายใน",
    "Wonder - YK Logistics": "ลูกค้า-อื่นๆ",
    "Y.K. & KTL งานหัวลาก": "ภายใน",
    "Y.K. & ปตท.คลองเจ็ด": "น้ำมัน",
    "Y.K. logistics/P&W ": "ซ่อมบำรุง",
    "Y.K. หัวลาก LCB. ": "ภายใน",
    "Y.K.พขร. ขับรถบริษัท": "ภายใน",
    "Y.K.ลอจิสติค&อู่เล็ก": "ซ่อมบำรุง",
    "Y.K.หัวลากธัญญะ Big C": "ภายใน",
    "YK & DHL ABF": "ลูกค้า-DHL",
    "YK & อู่ภูผา": "ซ่อมบำรุง",
    "YK at Yusen": "ลูกค้า-อื่นๆ",
    "YK งานซ่อม แหลม": "ซ่อมบำรุง",
    "YK-JGL": "ลูกค้า-อื่นๆ",
    "YK~DHL Overflow": "ลูกค้า-DHL",
    "งานโฮมโปร Y.K.": "ลูกค้า-อื่นๆ",
    "ซ่อมบำรุง YK": "ซ่อมบำรุง",
    "บอสรับเบอร์ & YK": "ลูกค้า-อื่นๆ",
    "ปะยาง ธัญญะ & YK": "ซ่อมบำรุง",
    "ร้านเครดิตท่าเรือการยาง": "ซ่อมบำรุง",
    "วาย.เค.ลอจิสติค": "ภายใน",
    "สำนักงานบัญชี YK": "ภายใน",
    "ออโต้ เทคนิค & YK": "ซ่อมบำรุง",
    "อู่ช่างไนท์ ซ่อมแอร์&ระบบไฟ": "ซ่อมบำรุง",
    "อู่ช่างไสว & YK": "ซ่อมบำรุง",
    "อู๋ช่างโก๋ & YK": "ซ่อมบำรุง",
    "เรียกรถ YK Logistic": "ลูกค้า-DHL",
    "ไทร์มาร์ท & YK": "ซ่อมบำรุง",
    "🚚หัวหน้างาน 🚛": "ภายใน",
}


def test_all_real_groups_categorized_correctly():
    wrong = {name: (category_for(name), expected)
             for name, expected in REAL_GROUPS.items()
             if category_for(name) != expected}
    assert not wrong, f"mis-categorized: {wrong}"


def test_dhl_wins_over_other_customer():
    # "SUB YK & DHL BPD" มีทั้ง DHL — ต้องลง DHL ไม่ใช่ลูกค้าอื่น
    assert category_for("SUB YK & DHL BPD") == "ลูกค้า-DHL"


def test_garage_keyword_wins_over_customer_default():
    # "อู่เล็ก" → ซ่อม ไม่ใช่ลูกค้า
    assert category_for("Y.K.ลอจิสติค&อู่เล็ก") == "ซ่อมบำรุง"


def test_pw_parts_shop_is_maintenance():
    assert category_for("Y.K. logistics/P&W ") == "ซ่อมบำรุง"
    assert category_for("P&W") == "ซ่อมบำรุง"


def test_future_parts_shop_keywords():
    # ร้านอะไหล่ในอนาคต Superpart / SPP
    assert category_for("Superpart & YK") == "ซ่อมบำรุง"
    assert category_for("SPP อะไหล่ YK") == "ซ่อมบำรุง"


def test_riakrot_is_dhl_chevrolet():
    assert category_for("เรียกรถ YK Logistic") == "ลูกค้า-DHL"


def test_unknown_falls_back_to_customer():
    assert category_for("กลุ่มใหม่ที่ไม่เคยเห็น") == "ลูกค้า-อื่นๆ"
    assert category_for("") == "ลูกค้า-อื่นๆ"
    assert category_for(None) == "ลูกค้า-อื่นๆ"
