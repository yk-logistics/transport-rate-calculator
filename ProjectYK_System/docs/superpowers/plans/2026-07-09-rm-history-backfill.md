# RM History Backfill — Implementation Plan

> **For agentic workers:** งานนี้เป็น **งานเงิน** (ค่าซ่อมเข้ารายงานต้นทุน) — ตาม `CLAUDE.md`
> ห้าม delegate ให้ subagent ตัวหลักต้องทำเอง ทีละ task พร้อมเทสต์

**Goal:** ดึงประวัติซ่อม 9,323 บิล / 20,333 บรรทัด (2018-2026) จาก Google Sheets 3 ไฟล์
เข้า `MaintRecord` + `MaintPart` โดยยอดรวมต่อคันต้องตรงกับยอดที่ชีทคำนวณไว้เอง

**Architecture:** แยก 3 ชั้น — (1) parser บริสุทธิ์ ไม่แตะ DB/เน็ต ทดสอบง่าย
(2) ชั้นเขียน DB ที่ idempotent ด้วย `import_key` (3) CLI ที่อ่านชีทและพิมพ์รายงาน
ทุกชั้นมี `dry_run` เป็นค่าเริ่มต้น

**Tech Stack:** Python 3.12 · SQLModel/SQLAlchemy · gspread (service account เดิม secret #7) · pytest

**สเปค:** `ProjectYK_System/docs/superpowers/specs/2026-07-09-rm-history-backfill-design.md`

## Global Constraints

- รันเทสต์: `cd ProjectYK_System/app && .venv/Scripts/python.exe -X utf8 -m pytest -q -p no:cacheprovider`
- SQLite `ALTER TABLE ... ADD COLUMN` **ห้ามมี UNIQUE** — unique index ต้องสร้างแยก
- Schema เปลี่ยน = ต้องบวก `SCHEMA_VERSION` ใน `main.py` พร้อมกันเสมอ
- `total_cost = (parts + labor + other) − discount + vat` — บันทึกเดิมที่ `discount=vat=0` ต้องได้ค่าเดิมเป๊ะ
- แท็บที่จับคู่ทะเบียนไม่ได้ → **ไม่ import ทั้งแท็บ** (ห้ามสร้าง record ลอย)
- วันที่แปลงไม่ได้ / เป็นอนาคต → ข้าม + บันทึก issue (ห้ามเดา)
- ทุก `MaintRecord` ที่ import มี `import_key` ขึ้นต้น `rm:<file_slug>:` — บันทึกที่คนคีย์เองมีค่าว่าง ห้ามโดนลบ

## File Structure

| ไฟล์ | หน้าที่ |
|------|---------|
| `app/models.py` (แก้) | `MaintPart.discount/vat` · `MaintRecord.discount/vat/import_key` |
| `app/main.py` (แก้) | `SCHEMA_VERSION=50` · migration · `_recompute_maint_costs()` ใหม่ |
| `app/services/rm_history.py` (ใหม่) | parser บริสุทธิ์: วันที่ / ทะเบียน / หมวด / แกะแท็บ |
| `app/services/rm_history_import.py` (ใหม่) | เขียน DB: vendor, MaintRecord+MaintPart, idempotent, rollback |
| `tools/import_rm_history.py` (ใหม่) | CLI: อ่านชีท → รายงาน → `--apply` → ตรวจทานยอด |
| `app/tests/test_maint_discount_vat.py` (ใหม่) | Task 1 |
| `app/tests/test_rm_history_parse.py` (ใหม่) | Task 2 |
| `app/tests/test_rm_history_import.py` (ใหม่) | Task 3 |

---

### Task 1: schema v50 — ช่องส่วนลด/VAT + สูตรยอดใหม่

**Files:**
- Modify: `ProjectYK_System/app/models.py` (`MaintPart`, `MaintRecord`)
- Modify: `ProjectYK_System/app/main.py` (`SCHEMA_VERSION`, `_apply_additive_migrations`, `_recompute_maint_costs`)
- Test: `ProjectYK_System/app/tests/test_maint_discount_vat.py`

**Interfaces:**
- Consumes: `_recompute_maint_costs(s: Session, rec: MaintRecord, force: tuple = ())` (มีอยู่แล้ว)
- Produces: `MaintPart.discount/vat: float` · `MaintRecord.discount/vat: float`, `MaintRecord.import_key: str`

- [ ] **Step 1: เขียนเทสต์ให้แดง**

`app/tests/test_maint_discount_vat.py`:

```python
# -*- coding: utf-8 -*-
"""v50: ส่วนลด + VAT ต่อบรรทัด → ยอดบิลตรงกับ "ราคาสุทธิ" ในชีท RM History.

เคสจริง (LCB 71-6802): ฝาครอบรีเลย์ 690 − ส่วนลด 103.50 + VAT 41.06 = 627.56
"""
import os
import tempfile
from datetime import date

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select

from db_config import engine
import main as appmod
from models import MaintPart, MaintRecord


@pytest.fixture()
def session():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        yield s


def _rec(s, **kw) -> MaintRecord:
    rec = MaintRecord(record_no=kw.pop("no", "M000001"), work_date=date(2021, 2, 18), **kw)
    s.add(rec); s.commit(); s.refresh(rec)
    return rec


def _line(s, rec_id, kind, qty, price, discount=0.0, vat=0.0):
    s.add(MaintPart(maint_record_id=rec_id, kind=kind, part_name_raw="x",
                    qty=qty, unit_price=price, total=qty * price,
                    discount=discount, vat=vat))
    s.commit()


def test_discount_and_vat_reach_record_total(session):
    rec = _rec(session)
    _line(session, rec.id, "part", 1, 690.0, discount=103.50, vat=41.06)
    appmod._recompute_maint_costs(session, rec)
    session.add(rec); session.commit()

    assert rec.parts_cost == 690.0        # ก่อนหักส่วนลด ก่อน VAT (ตรงช่อง "รวม")
    assert rec.discount == 103.50
    assert rec.vat == 41.06
    assert round(rec.total_cost, 2) == 627.56


def test_legacy_record_without_discount_unchanged(session):
    """บิลเดิม (บิลร้านยาง 4,100) ต้องได้ยอดเดิมทุกบาท — ห้าม regression."""
    rec = _rec(session, no="M000002")
    _line(session, rec.id, "service", 1, 1200.0)
    _line(session, rec.id, "labor", 1, 500.0)
    _line(session, rec.id, "part", 2, 200.0)
    _line(session, rec.id, "part", 8, 250.0)
    appmod._recompute_maint_costs(session, rec)

    assert rec.parts_cost == 2400.0 and rec.labor_cost == 500.0 and rec.other_cost == 1200.0
    assert rec.discount == 0.0 and rec.vat == 0.0
    assert rec.total_cost == 4100.0


def test_manual_costs_no_lines_keep_zero_discount(session):
    """บันทึกเก่าที่คีย์ยอดมือ ไม่มีบรรทัด → ห้ามแตะ discount/vat/total."""
    rec = _rec(session, no="M000003", parts_cost=1200.0, labor_cost=800.0, total_cost=2000.0)
    appmod._recompute_maint_costs(session, rec)
    assert rec.parts_cost == 1200.0 and rec.labor_cost == 800.0
    assert rec.discount == 0.0 and rec.vat == 0.0 and rec.total_cost == 2000.0


def test_migration_adds_columns_and_unique_index(session):
    from sqlalchemy import text
    with engine.begin() as conn:
        part_cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(maintpart)")]
        rec_cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(maintrecord)")]
        idx = [r[1] for r in conn.exec_driver_sql("PRAGMA index_list(maintrecord)")]
    assert "discount" in part_cols and "vat" in part_cols
    assert {"discount", "vat", "import_key"} <= set(rec_cols)
    assert "ux_maintrecord_import_key" in idx


def test_import_key_unique_but_blank_allowed(session):
    """บันทึกที่คนคีย์เอง (import_key='') มีได้หลายแถว; คีย์ที่ import ห้ามซ้ำ."""
    from sqlalchemy.exc import IntegrityError
    session.add(MaintRecord(record_no="M100", work_date=date(2024, 1, 1), import_key=""))
    session.add(MaintRecord(record_no="M101", work_date=date(2024, 1, 1), import_key=""))
    session.commit()
    session.add(MaintRecord(record_no="M102", work_date=date(2024, 1, 1), import_key="rm:lcb:abc"))
    session.commit()
    session.add(MaintRecord(record_no="M103", work_date=date(2024, 1, 1), import_key="rm:lcb:abc"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
```

- [ ] **Step 2: รันให้เห็นแดง**

```bash
cd ProjectYK_System/app && .venv/Scripts/python.exe -X utf8 -m pytest tests/test_maint_discount_vat.py -q -p no:cacheprovider
```
คาด: FAIL — `MaintPart() got an unexpected keyword argument 'discount'`

- [ ] **Step 3: เพิ่มคอลัมน์ใน `models.py`**

ใน `class MaintPart` (ใต้ `total`):

```python
    discount: float = 0.0      # v50: ส่วนลดต่อบรรทัด (จากบิลร้าน)
    vat: float = 0.0           # v50: ภาษีมูลค่าเพิ่มต่อบรรทัด
```

ใน `class MaintRecord` (ใต้ `other_cost`):

```python
    discount: float = 0.0      # v50: Σ MaintPart.discount
    vat: float = 0.0           # v50: Σ MaintPart.vat
    # v50: ลายเซ็นแถวต้นทาง "rm:<file>:<sha1>" — ว่าง = คนคีย์เอง (rollback ไม่แตะ)
    # ห้ามใส่ index=True: SQLModel จะสร้าง ix_maintrecord_import_key แบบ **ไม่ unique**
    # ชนชื่อกับ partial unique index ด้านล่าง (CREATE ... IF NOT EXISTS จะเงียบแล้วไม่ unique)
    import_key: str = ""
```

- [ ] **Step 4: migration ใน `main.py`**

`SCHEMA_VERSION = 50` (เติมคำอธิบายไว้หน้าสุด):

```python
SCHEMA_VERSION = 50  # v50: MaintPart.discount/vat + MaintRecord.discount/vat/import_key (ALTER — ดึงประวัติซ่อมย้อนหลังจาก RM History sheets); v49: MaintPart.kind ...
```

ใน `_apply_additive_migrations()` ต่อจากบล็อก v49:

```python
    # v49 → v50: ส่วนลด/VAT ต่อบรรทัด + ลายเซ็นแถวต้นทาง (ดึงประวัติซ่อมย้อนหลัง)
    _ensure_column("maintpart",   "discount",   "REAL", default="0")
    _ensure_column("maintpart",   "vat",        "REAL", default="0")
    _ensure_column("maintrecord", "discount",   "REAL", default="0")
    _ensure_column("maintrecord", "vat",        "REAL", default="0")
    _ensure_column("maintrecord", "import_key", "TEXT", default="")
    if IS_SQLITE:
        # ALTER ADD COLUMN ... UNIQUE ทำไม่ได้ → partial unique index (ค่าว่างซ้ำได้)
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_maintrecord_import_key "
                "ON maintrecord(import_key) WHERE import_key != ''")
```

- [ ] **Step 5: สูตรยอดใหม่ใน `_recompute_maint_costs`**

แทนที่ตัวเดิมทั้งฟังก์ชัน:

```python
def _recompute_maint_costs(s: Session, rec: MaintRecord, force: tuple = ()) -> None:
    """ยอดรวมของบันทึกซ่อม = ผลรวมบรรทัดแยกตามหมวด (v49) + ส่วนลด/VAT (v50).

    หมวดไหน **ไม่มีบรรทัดเลย** ให้คงยอดที่คีย์มือไว้ — บันทึกเก่ามีแต่บรรทัดอะไหล่
    กับค่าแรงที่คีย์มือ ห้ามล้างเป็น 0. `force` = หมวดที่เพิ่งลบบรรทัดสุดท้ายทิ้ง
    (ต้องคำนวณใหม่ให้เป็น 0 จริงๆ).
    total_cost = (อะไหล่+ค่าแรง+บริการ) − ส่วนลด + VAT = เงินที่จ่ายจริง
    """
    lines = s.exec(select(MaintPart).where(MaintPart.maint_record_id == rec.id)).all()
    sums = {"part": 0.0, "labor": 0.0, "service": 0.0}
    for ln in lines:
        sums[ln.kind if ln.kind in sums else "part"] += ln.total or 0
    have = {ln.kind for ln in lines} | set(force)
    if "part" in have:
        rec.parts_cost = sums["part"]
    if "labor" in have:
        rec.labor_cost = sums["labor"]
    if "service" in have:
        rec.other_cost = sums["service"]      # บริการ → ช่อง "ค่าอื่นๆ" เดิม
    if lines:
        rec.discount = sum(ln.discount or 0 for ln in lines)
        rec.vat = sum(ln.vat or 0 for ln in lines)
    rec.total_cost = (round((rec.parts_cost or 0) + (rec.labor_cost or 0)
                            + (rec.other_cost or 0) - (rec.discount or 0)
                            + (rec.vat or 0), 2))
    rec.updated_at = datetime.utcnow()
```

- [ ] **Step 6: รันเทสต์ Task 1 + เทสต์ที่เกี่ยวข้องเดิม**

```bash
cd ProjectYK_System/app && .venv/Scripts/python.exe -X utf8 -m pytest tests/test_maint_discount_vat.py tests/test_maint_line_kinds.py tests/test_bill_ocr.py tests/test_tire_bill_report.py -q -p no:cacheprovider
```
คาด: PASS ทั้งหมด (บิล 4,100 ต้องยังได้ 4,100)

- [ ] **Step 7: ชุดเต็ม**

```bash
cd ProjectYK_System/app && .venv/Scripts/python.exe -X utf8 -m pytest -q -p no:cacheprovider
```
คาด: 609 + 5 = 614 ผ่าน

- [ ] **Step 8: preflight + deploy**

```bash
# นับแถวจริงบน production ก่อน (ต้องเป็น maintrecord 1 / maintpart 0)
ssh yklog@100.97.150.114 "..."   # อ่านอย่างเดียว
bash ProjectYK_System/tools/deploy_mvp.sh --markers "import_key,ux_maintrecord_import_key"
```

- [ ] **Step 9: Commit**

```bash
git add ProjectYK_System/app/models.py ProjectYK_System/app/main.py ProjectYK_System/app/tests/test_maint_discount_vat.py
git commit -m "feat(maint): schema v50 ส่วนลด/VAT ต่อบรรทัด + import_key (เตรียมดึงประวัติซ่อม)"
```

---

### Task 2: parser บริสุทธิ์ `services/rm_history.py`

**Files:**
- Create: `ProjectYK_System/app/services/rm_history.py`
- Test: `ProjectYK_System/app/tests/test_rm_history_parse.py`

**Interfaces:**
- Consumes: ไม่มี (ไม่แตะ DB/เน็ต)
- Produces:
  - `parse_date(raw: str, today: date | None = None) -> date | None`
  - `normalize_plate(tab_title: str) -> str | None`
  - `classify_kind(detail: str) -> str`  (`"part" | "labor" | "service"`)
  - `parse_tab(tab_title: str, values: list[list[str]]) -> ParsedTab`
  - `@dataclass ParsedTab: plate: str | None; header_row: int; bills: list[Bill]; issues: list[dict]`
  - `@dataclass Bill: work_date: date; mile: float; vendor: str; sheet_row: int; lines: list[dict]`
  - `Bill.lines[i] = {"kind","name","qty","unit_price","total","discount","vat","net"}`
  - `@dataclass ParsedTab.sheet_net_total: float | None`  (ยอดสุทธิที่ชีทคำนวณไว้ — แถว "รายการซ่อมรถ")

- [ ] **Step 1: เขียนเทสต์ให้แดง**

`app/tests/test_rm_history_parse.py`:

```python
# -*- coding: utf-8 -*-
"""แกะแท็บ RM History — pure functions ไม่แตะ DB/เน็ต (ข้อมูลจริงย่อส่วน)."""
from datetime import date

import pytest

from services import rm_history as rm


# ---- วันที่: ห้ามเดา ----------------------------------------------------------
@pytest.mark.parametrize("raw,expect", [
    ("13/05/20", date(2020, 5, 13)),        # 2 หลัก 00-40 = ค.ศ.
    ("18/02/2021", date(2021, 2, 18)),      # 4 หลัก ค.ศ.
    ("1/3/67", date(2024, 3, 1)),           # 2 หลัก 60-79 = พ.ศ.
    ("05/11/2566", date(2023, 11, 5)),      # 4 หลัก พ.ศ.
    (" 04/08/20 ", date(2020, 8, 4)),       # เว้นวรรครอบๆ
])
def test_parse_date_ok(raw, expect):
    assert rm.parse_date(raw, today=date(2026, 7, 9)) == expect


@pytest.mark.parametrize("raw", ["", "-", "31/02/24", "13/05/29", "13/05/02", "abc", "45123"])
def test_parse_date_refuses(raw):
    """/29 = อนาคต · /02 = กำกวม · 31/02 = ไม่มีจริง → None (ไปลง issue)"""
    assert rm.parse_date(raw, today=date(2026, 7, 9)) is None


# ---- ทะเบียน -----------------------------------------------------------------
@pytest.mark.parametrize("tab,expect", [
    ("71-6802", "71-6802"),
    ("71-6802 อย", "71-6802"),
    ("72-2294(หางใหม่)", "72-2294"),
    (" 71-1802 ", "71-1802"),
])
def test_normalize_plate_ok(tab, expect):
    assert rm.normalize_plate(tab) == expect


@pytest.mark.parametrize("tab", ["หน้ารวม", "ชีต3", "ตู้1", "รับรถ 8682",
                                 "Stock  LCB", "แบตเตอรี่", "บษ2681"])
def test_normalize_plate_rejects_non_vehicle(tab):
    assert rm.normalize_plate(tab) is None


# ---- หมวดบรรทัด ---------------------------------------------------------------
@pytest.mark.parametrize("detail,kind", [
    ("ค่าแรงถอดยาง", "labor"),
    ("ค่าแรง", "labor"),
    ("บริการพ่นน้ำยาฆ่าเชื้อ", "service"),
    ("ตรวจแผ่นกรองอากาศ", "service"),
    ("อัดจารบีช่วงล่าง", "service"),
    ("น้ำกลั่น", "part"),
    ("ฝาครอบรีเลย์", "part"),
])
def test_classify_kind(detail, kind):
    assert rm.classify_kind(detail) == kind


# ---- แกะทั้งแท็บ ---------------------------------------------------------------
HDR = ["วันที่", "เลขกิโลเมตร", "บริษัท", "รายละเอียด", "จำนวน", "ราคา", "รวม",
       "ส่วนลด", "ภาษีมูลค่าเพิ่ม", "ราคาสุทธิ", "หมายเหตุ"]

TAB = [
    ["71-6802", "Isuzu"],                                    # 1
    [], [], [],                                              # 2-4
    ["รายการซ่อมรถ", "", "", "", "", " 700.00 ", " 700.00 ", " 103.50 ", " 41.76 ", " 638.26 "],   # 5
    HDR,                                                     # 6  ← header อยู่แถว 6
    ["", "", "", "", " Time/Qty", " Price", " Sum", " Discount", " Vat %", " Amount"],             # 7
    ["13/05/20", "12,029", "Isuzu บางปะอิน", "บริการพ่นน้ำยา", " 1.00 ", " -  ", " -  ", "", " -  ", " -  "],  # 8
    ["", "", "", "น้ำกลั่น", " 1.00 ", " 10.00 ", " 10.00 ", "", " 0.70 ", " 10.70 "],            # 9
    [],                                                       # 10 ว่าง → ข้ามเงียบ
    ["18/02/21", "", "Isuzu บางปะอิน", "ฝาครอบรีเลย์", " 1.00 ", " 690.00 ", " 690.00 ", " 103.50 ", " 41.06 ", " 627.56 "],  # 11
    ["13/05/29", "", "ร้านผี", "ของว่าง", " 1.00 ", " 5.00 ", " 5.00 ", "", "", " 5.00 "],        # 12 อนาคต → issue
]


def test_parse_tab_groups_lines_under_bill():
    p = rm.parse_tab("71-6802", TAB)
    assert p.plate == "71-6802"
    assert p.header_row == 6
    assert p.sheet_net_total == 638.26

    assert len(p.bills) == 2
    b1 = p.bills[0]
    assert b1.work_date == date(2020, 5, 13) and b1.mile == 12029.0
    assert b1.vendor == "Isuzu บางปะอิน"
    assert len(b1.lines) == 2                      # วันที่ว่าง = บรรทัดต่อของบิลเดิม
    assert b1.lines[1]["name"] == "น้ำกลั่น" and b1.lines[1]["net"] == 10.70

    b2 = p.bills[1]
    assert b2.work_date == date(2021, 2, 18)
    assert b2.lines[0]["discount"] == 103.50 and b2.lines[0]["vat"] == 41.06
    assert b2.lines[0]["kind"] == "part"
    assert b2.sheet_row == 11


def test_parse_tab_records_issue_for_bad_date():
    p = rm.parse_tab("71-6802", TAB)
    reasons = [i["reason"] for i in p.issues]
    assert any("วันที่" in r for r in reasons)
    assert all(b.work_date.year != 2029 for b in p.bills)   # บิลผีไม่เข้า


def test_parse_tab_missing_header_returns_issue():
    p = rm.parse_tab("หน้ารวม", [["ทะเบียน", "ยี่ห้อ"], ["71-8000", "Isuzu"]])
    assert p.bills == [] and p.header_row == 0
    assert any("หัวตาราง" in i["reason"] for i in p.issues)
```

- [ ] **Step 2: รันให้เห็นแดง**

```bash
cd ProjectYK_System/app && .venv/Scripts/python.exe -X utf8 -m pytest tests/test_rm_history_parse.py -q -p no:cacheprovider
```
คาด: FAIL — `ModuleNotFoundError: No module named 'services.rm_history'`

- [ ] **Step 3: เขียน `services/rm_history.py`**

```python
# -*- coding: utf-8 -*-
"""แกะตารางประวัติซ่อม (RM History Google Sheets) → บิล + บรรทัดรายการ.

pure functions: ไม่แตะ DB ไม่แตะเน็ต → เทสต์ได้ตรงๆ
กฎเหล็ก: อ่านไม่ออก = คืน None/ลง issues ห้ามเดา (ค่าซ่อมไปโผล่ผิดปีแล้วหายาก)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

_LABOR = ("ค่าแรง", "ค่าถอด", "ค่าประกอบ", "แรงงาน")
_SERVICE = ("บริการ", "ตรวจ", "เช็ค", "อัดจารบี", "เปลี่ยนถ่าย", "ค่าเดินทาง", "ล้าง")
_PLATE_RE = re.compile(r"^\d{2}-\d{4}$")
_DATE_RE = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{2,4})\s*$")
_REQUIRED_HEADERS = ("วันที่", "บริษัท", "รายละเอียด", "จำนวน", "ราคา", "รวม", "ราคาสุทธิ")


@dataclass
class Bill:
    work_date: date
    mile: float
    vendor: str
    sheet_row: int
    lines: list[dict] = field(default_factory=list)


@dataclass
class ParsedTab:
    plate: str | None
    header_row: int
    bills: list[Bill] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)
    sheet_net_total: float | None = None


def _num(v) -> float:
    s = str(v or "").replace(",", "").strip()
    if not s or s == "-":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_date(raw: str, today: date | None = None) -> date | None:
    """dd/mm/yy(yy) — พ.ศ./ค.ศ. ปนกันในไฟล์เดียว. อ่านไม่ออก/อนาคต = None."""
    today = today or date.today()
    m = _DATE_RE.match(str(raw or ""))
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if len(m.group(3)) == 4:
        year = y - 543 if y >= 2500 else y
        if not (1990 <= year <= 2100):
            return None
    elif 60 <= y <= 79:            # พ.ศ. 2 หลัก
        year = 2500 + y - 543
    elif 0 <= y <= 40:             # ค.ศ. 2 หลัก
        year = 2000 + y
    else:
        return None
    try:
        out = date(year, mo, d)
    except ValueError:
        return None
    return None if out > today else out


def normalize_plate(tab_title: str) -> str | None:
    """ชื่อแท็บ → ทะเบียนมาตรฐาน; ไม่ใช่รูปแบบทะเบียน = None (ไม่ใช่แท็บรถ)."""
    t = re.sub(r"\(.*?\)", "", str(tab_title or ""))
    t = re.sub(r"\s*อย\.?\s*$", "", t.strip())
    t = t.strip()
    return t if _PLATE_RE.match(t) else None


def classify_kind(detail: str) -> str:
    d = str(detail or "")
    if any(k in d for k in _LABOR):
        return "labor"
    if any(k in d for k in _SERVICE):
        return "service"
    return "part"


def _find_header(values: list[list[str]]) -> int:
    """คืนเลขแถว (1-based) ของหัวตาราง — หัวอยู่คนละแถวกันทุกแท็บ ห้ามล็อกเลข."""
    for i, row in enumerate(values):
        if row and str(row[0]).strip() == "วันที่" and len(row) > 3:
            return i + 1
    return 0


def _col_map(header: list[str]) -> dict[str, int]:
    return {str(v).strip(): i for i, v in enumerate(header) if str(v).strip()}


def parse_tab(tab_title: str, values: list[list[str]]) -> ParsedTab:
    plate = normalize_plate(tab_title)
    hdr = _find_header(values)
    p = ParsedTab(plate=plate, header_row=hdr)
    if not hdr:
        p.issues.append({"row": 0, "reason": "ไม่พบหัวตาราง (คอลัมน์แรกต้องเป็น 'วันที่')",
                         "raw": tab_title})
        return p

    col = _col_map(values[hdr - 1])
    missing = [h for h in _REQUIRED_HEADERS if h not in col]
    if missing:
        p.issues.append({"row": hdr, "reason": f"หัวตารางขาด: {', '.join(missing)}",
                         "raw": tab_title})
        return p

    # ยอดสุทธิที่ชีทคำนวณไว้ (แถว "รายการซ่อมรถ" เหนือหัวตาราง) — ใช้ตรวจทานหลัง import
    for row in values[max(0, hdr - 4):hdr - 1]:
        if row and "รายการซ่อมรถ" in str(row[0]):
            j = col["ราคาสุทธิ"]
            if len(row) > j:
                p.sheet_net_total = _num(row[j])
            break

    def cell(row, name):
        j = col[name]
        return row[j] if len(row) > j else ""

    cur: Bill | None = None
    for i in range(hdr + 1, len(values) + 1):
        row = values[i - 1]
        if not row or not any(str(c).strip() for c in row):
            continue
        raw_date = str(cell(row, "วันที่")).strip()
        detail = str(cell(row, "รายละเอียด")).strip()

        if raw_date:
            d = parse_date(raw_date)
            if d is None:
                p.issues.append({"row": i, "reason": f"วันที่อ่านไม่ออก/อนาคต: {raw_date!r}",
                                 "raw": detail})
                cur = None                      # ทิ้งทั้งบิล รวมบรรทัดต่อของมัน
                continue
            cur = Bill(work_date=d, mile=_num(cell(row, "เลขกิโลเมตร")),
                       vendor=str(cell(row, "บริษัท")).strip(), sheet_row=i)
            p.bills.append(cur)

        if not detail:
            continue
        if cur is None:
            p.issues.append({"row": i, "reason": "บรรทัดไม่มีบิลแม่ (วันที่ก่อนหน้าใช้ไม่ได้)",
                             "raw": detail})
            continue
        total = _num(cell(row, "รวม")) or _num(cell(row, "จำนวน")) * _num(cell(row, "ราคา"))
        cur.lines.append({
            "kind": classify_kind(detail), "name": detail,
            "qty": _num(cell(row, "จำนวน")) or 1.0,
            "unit_price": _num(cell(row, "ราคา")),
            "total": total,
            "discount": _num(cell(row, "ส่วนลด")),
            "vat": _num(cell(row, "ภาษีมูลค่าเพิ่ม")),
            "net": _num(cell(row, "ราคาสุทธิ")),
        })

    p.bills = [b for b in p.bills if b.lines]     # บิลที่ไม่มีบรรทัดเลย = ไม่มีความหมาย
    return p
```

- [ ] **Step 4: รันให้เขียว**

```bash
cd ProjectYK_System/app && .venv/Scripts/python.exe -X utf8 -m pytest tests/test_rm_history_parse.py -q -p no:cacheprovider
```
คาด: PASS ทั้งหมด

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/app/services/rm_history.py ProjectYK_System/app/tests/test_rm_history_parse.py
git commit -m "feat(rm-history): parser แกะแท็บประวัติซ่อม (วันที่ พ.ศ./ค.ศ. + fill-down บิล)"
```

---

### Task 3: ชั้นเขียน DB `services/rm_history_import.py`

**Files:**
- Create: `ProjectYK_System/app/services/rm_history_import.py`
- Test: `ProjectYK_System/app/tests/test_rm_history_import.py`

**Interfaces:**
- Consumes: `rm_history.ParsedTab`, `rm_history.Bill` (Task 2) · `MaintRecord.import_key` (Task 1)
- Produces:
  - `SHEETS: dict[str, str]`  → `{"bigc": "<sheet_id>", "wangnoi": "...", "lcb": "..."}`
  - `make_import_key(file_slug: str, sheet_id: str, tab: str, first_row: int) -> str`
  - `import_tab(session, file_slug, sheet_id, tab, parsed, dry_run=True) -> dict` (stats)
  - `rollback_file(session, file_slug, dry_run=True) -> int`
  - stats keys: `bills`, `lines`, `skipped_dup`, `skipped_tab`, `new_vendors`, `system_net`

- [ ] **Step 1: เขียนเทสต์ให้แดง**

`app/tests/test_rm_history_import.py`:

```python
# -*- coding: utf-8 -*-
"""เขียนประวัติซ่อมลง DB — dry-run เป็นค่าเริ่มต้น, ยิงซ้ำไม่เกิดซ้ำ, จับคู่รถไม่ได้ = ไม่เขียน."""
import os
import tempfile
from datetime import date

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select

from db_config import engine
import main as appmod
from models import MaintPart, MaintRecord, Vehicle, Vendor
from services import rm_history as rm
from services import rm_history_import as rmi

SHEET_ID = "SHEETLCB"


def _parsed(plate="71-6802"):
    p = rm.ParsedTab(plate=plate, header_row=6, sheet_net_total=638.26)
    b = rm.Bill(work_date=date(2021, 2, 18), mile=12029.0,
                vendor="Isuzu บางปะอิน", sheet_row=11)
    b.lines = [{"kind": "part", "name": "ฝาครอบรีเลย์", "qty": 1.0, "unit_price": 690.0,
                "total": 690.0, "discount": 103.50, "vat": 41.06, "net": 627.56}]
    p.bills = [b]
    return p


@pytest.fixture()
def session():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        s.add(Vehicle(plate_no="71-6802", site_code="LCB"))
        s.commit()
        yield s


def test_dry_run_writes_nothing(session):
    stats = rmi.import_tab(session, "lcb", SHEET_ID, "71-6802", _parsed(), dry_run=True)
    assert stats["bills"] == 1 and stats["lines"] == 1
    assert session.exec(select(MaintRecord)).first() is None
    assert session.exec(select(Vendor)).first() is None


def test_apply_creates_record_lines_and_vendor(session):
    rmi.import_tab(session, "lcb", SHEET_ID, "71-6802", _parsed(), dry_run=False)
    rec = session.exec(select(MaintRecord)).one()
    line = session.exec(select(MaintPart)).one()
    vendor = session.exec(select(Vendor)).one()

    assert rec.vehicle_id is not None and rec.plate_raw == "71-6802"
    assert rec.mile_snapshot == 12029.0 and rec.vendor_id == vendor.id
    assert rec.import_key.startswith("rm:lcb:")
    assert round(rec.total_cost, 2) == 627.56 and rec.discount == 103.50
    assert line.kind == "part" and line.vat == 41.06


def test_second_run_is_idempotent(session):
    rmi.import_tab(session, "lcb", SHEET_ID, "71-6802", _parsed(), dry_run=False)
    stats = rmi.import_tab(session, "lcb", SHEET_ID, "71-6802", _parsed(), dry_run=False)
    assert stats["skipped_dup"] == 1
    assert len(session.exec(select(MaintRecord)).all()) == 1
    assert len(session.exec(select(MaintPart)).all()) == 1


def test_unmatched_plate_writes_nothing(session):
    p = _parsed(plate="99-9999")
    stats = rmi.import_tab(session, "lcb", SHEET_ID, "99-9999", p, dry_run=False)
    assert stats["skipped_tab"] == 1 and stats["bills"] == 0
    assert session.exec(select(MaintRecord)).first() is None


def test_non_vehicle_tab_writes_nothing(session):
    p = rm.ParsedTab(plate=None, header_row=0)
    stats = rmi.import_tab(session, "lcb", SHEET_ID, "หน้ารวม", p, dry_run=False)
    assert stats["skipped_tab"] == 1
    assert session.exec(select(MaintRecord)).first() is None


def test_rollback_only_touches_imported_rows(session):
    rmi.import_tab(session, "lcb", SHEET_ID, "71-6802", _parsed(), dry_run=False)
    hand = MaintRecord(record_no="M999999", work_date=date(2026, 1, 1), import_key="")
    session.add(hand); session.commit()

    n = rmi.rollback_file(session, "lcb", dry_run=True)
    assert n == 1 and len(session.exec(select(MaintRecord)).all()) == 2

    n = rmi.rollback_file(session, "lcb", dry_run=False)
    assert n == 1
    rows = session.exec(select(MaintRecord)).all()
    assert len(rows) == 1 and rows[0].record_no == "M999999"   # บันทึกที่คนคีย์เองรอด
    assert session.exec(select(MaintPart)).first() is None
```

- [ ] **Step 2: รันให้เห็นแดง**

```bash
cd ProjectYK_System/app && .venv/Scripts/python.exe -X utf8 -m pytest tests/test_rm_history_import.py -q -p no:cacheprovider
```
คาด: FAIL — `No module named 'services.rm_history_import'`

- [ ] **Step 3: เขียน `services/rm_history_import.py`**

```python
# -*- coding: utf-8 -*-
"""เขียนบิลจาก RM History ลง DB — idempotent + rollback ได้ + dry-run เป็นค่าเริ่มต้น.

กฎเงิน: จับคู่ทะเบียนไม่ได้ = ไม่เขียนทั้งแท็บ (ห้ามมี MaintRecord ลอยไม่มีเจ้าของ)
"""
from __future__ import annotations

import hashlib

from sqlalchemy import delete
from sqlmodel import Session, select

from models import MaintPart, MaintRecord, Vehicle, Vendor
from services.rm_history import ParsedTab

SHEETS = {
    "bigc":    "1rM00xNmUVL3XT4lCHf8Ooh9FHRlFp211cIrkszoCZXE",
    "wangnoi": "1trglO8b727sUcGC5n7kd3v2aYnXf9h0su8eJGtOzfOw",
    "lcb":     "169mraSWWU0l9HOL7_dkKCVIMZU5vlaWXspAK2ItDUnQ",
}


def make_import_key(file_slug: str, sheet_id: str, tab: str, first_row: int) -> str:
    """ขึ้นต้นด้วย rm:<file>: เพื่อให้ rollback กรองตามไฟล์ได้ (sha1 ล้วนกรองไม่ได้)."""
    h = hashlib.sha1(f"{sheet_id}|{tab}|{first_row}".encode()).hexdigest()[:16]
    return f"rm:{file_slug}:{h}"


def _next_record_no(session: Session) -> str:
    rows = session.exec(select(MaintRecord.record_no)).all()
    n = max((int(r[1:]) for r in rows if r and r[0] == "M" and r[1:].isdigit()), default=0)
    return f"M{n + 1:06d}"


def _find_or_create_vendor(session: Session, name: str, dry_run: bool) -> tuple[int | None, bool]:
    clean = " ".join((name or "").split())
    if not clean:
        return None, False
    v = session.exec(select(Vendor).where(Vendor.name == clean)).first()
    if v:
        return v.id, False
    if dry_run:
        return None, True
    codes = session.exec(select(Vendor.code)).all()
    n = max((int(c[1:]) for c in codes if c and c[0] == "V" and c[1:].isdigit()), default=0)
    v = Vendor(code=f"V{n + 1:04d}", name=clean, kind="service")
    session.add(v)
    session.commit()
    session.refresh(v)
    return v.id, True


def import_tab(session: Session, file_slug: str, sheet_id: str, tab: str,
               parsed: ParsedTab, dry_run: bool = True) -> dict:
    stats = {"bills": 0, "lines": 0, "skipped_dup": 0, "skipped_tab": 0,
             "new_vendors": [], "system_net": 0.0}

    vehicle = None
    if parsed.plate:
        vehicle = session.exec(select(Vehicle).where(Vehicle.plate_no == parsed.plate)).first()
    if vehicle is None:
        stats["skipped_tab"] = 1
        return stats

    for bill in parsed.bills:
        key = make_import_key(file_slug, sheet_id, tab, bill.sheet_row)
        exists = session.exec(select(MaintRecord).where(MaintRecord.import_key == key)).first()
        if exists:
            stats["skipped_dup"] += 1
            continue

        vendor_id, is_new = _find_or_create_vendor(session, bill.vendor, dry_run)
        if is_new and bill.vendor not in stats["new_vendors"]:
            stats["new_vendors"].append(" ".join(bill.vendor.split()))

        parts = sum(l["total"] for l in bill.lines if l["kind"] == "part")
        labor = sum(l["total"] for l in bill.lines if l["kind"] == "labor")
        other = sum(l["total"] for l in bill.lines if l["kind"] == "service")
        disc = sum(l["discount"] for l in bill.lines)
        vat = sum(l["vat"] for l in bill.lines)
        net = round(parts + labor + other - disc + vat, 2)

        stats["bills"] += 1
        stats["lines"] += len(bill.lines)
        stats["system_net"] = round(stats["system_net"] + net, 2)
        if dry_run:
            continue

        rec = MaintRecord(
            record_no=_next_record_no(session), work_date=bill.work_date,
            vehicle_id=vehicle.id, plate_raw=parsed.plate, mile_snapshot=bill.mile,
            kind="repair", status="done", vendor_id=vendor_id,
            parts_cost=parts, labor_cost=labor, other_cost=other,
            discount=disc, vat=vat, total_cost=net,
            import_key=key, notes=f"นำเข้าจาก RM History ({file_slug}!{tab} แถว {bill.sheet_row})")
        session.add(rec)
        session.commit()
        session.refresh(rec)
        for l in bill.lines:
            session.add(MaintPart(
                maint_record_id=rec.id, kind=l["kind"], part_name_raw=l["name"],
                qty=l["qty"], unit_price=l["unit_price"], total=l["total"],
                discount=l["discount"], vat=l["vat"]))
        session.commit()
    return stats


def rollback_file(session: Session, file_slug: str, dry_run: bool = True) -> int:
    """ลบเฉพาะแถวที่ import จากไฟล์นี้ — บันทึกที่คนคีย์เอง (import_key='') ไม่โดนแตะ."""
    prefix = f"rm:{file_slug}:"
    recs = session.exec(select(MaintRecord).where(
        MaintRecord.import_key.startswith(prefix))).all()   # type: ignore[union-attr]
    if dry_run or not recs:
        return len(recs)
    ids = [r.id for r in recs]
    session.exec(delete(MaintPart).where(MaintPart.maint_record_id.in_(ids)))  # type: ignore[attr-defined]
    session.exec(delete(MaintRecord).where(MaintRecord.id.in_(ids)))           # type: ignore[attr-defined]
    session.commit()
    return len(ids)
```

- [ ] **Step 4: รันให้เขียว**

```bash
cd ProjectYK_System/app && .venv/Scripts/python.exe -X utf8 -m pytest tests/test_rm_history_import.py -q -p no:cacheprovider
```
คาด: PASS 6 ข้อ

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/app/services/rm_history_import.py ProjectYK_System/app/tests/test_rm_history_import.py
git commit -m "feat(rm-history): เขียน DB แบบ idempotent + rollback เฉพาะแถวที่ import"
```

---

### Task 4: CLI `tools/import_rm_history.py`

**Files:**
- Create: `ProjectYK_System/tools/import_rm_history.py`

**Interfaces:**
- Consumes: `rm_history.parse_tab`, `rm_history_import.{SHEETS, import_tab, rollback_file}`
- Produces: CLI — `--dry-run` (ค่าเริ่มต้น) · `--apply` · `--rollback` · `--file {bigc,wangnoi,lcb,all}`

- [ ] **Step 1: เขียนสคริปต์**

```python
# -*- coding: utf-8 -*-
"""ดึงประวัติซ่อมจาก RM History Google Sheets → MaintRecord/MaintPart.

    python tools/import_rm_history.py --file lcb            # dry-run (ค่าเริ่มต้น)
    python tools/import_rm_history.py --file lcb --apply
    python tools/import_rm_history.py --file lcb --rollback --yes

อ่านชีทด้วย service account เดิม (noble-history-*.json) แบบ values_batch_get (1 call/ไฟล์)
"""
import argparse
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))

import gspread                                    # noqa: E402
from sqlmodel import Session                      # noqa: E402

from db_config import engine                      # noqa: E402
from services import rm_history as rm             # noqa: E402
from services import rm_history_import as rmi     # noqa: E402

KEY_FILE = next(Path(__file__).resolve().parents[2].glob("noble-history-*.json"))


def fetch(sheet_id: str) -> dict[str, list[list[str]]]:
    gc = gspread.service_account(filename=str(KEY_FILE))
    sh = gc.open_by_key(sheet_id)
    tabs = [w.title for w in sh.worksheets()]
    got = sh.values_batch_get([f"'{t}'!A1:K600" for t in tabs])["valueRanges"]
    return {t: vr.get("values", []) for t, vr in zip(tabs, got)}


def run(file_slug: str, apply: bool) -> None:
    sheet_id = rmi.SHEETS[file_slug]
    data = fetch(sheet_id)
    total = {"bills": 0, "lines": 0, "skipped_dup": 0, "skipped_tab": 0}
    vendors, issues, recon = [], [], []

    with Session(engine) as s:
        for tab, values in data.items():
            parsed = rm.parse_tab(tab, values)
            st = rmi.import_tab(s, file_slug, sheet_id, tab, parsed, dry_run=not apply)
            for k in total:
                total[k] += st[k]
            for v in st["new_vendors"]:
                if v not in vendors:
                    vendors.append(v)
            issues += [{"tab": tab, **i} for i in parsed.issues]
            if parsed.plate and st["skipped_tab"] == 0 and parsed.sheet_net_total is not None:
                recon.append((tab, parsed.sheet_net_total, st["system_net"]))

    print(f"\n=== {file_slug} ({'APPLY' if apply else 'DRY-RUN'}) ===")
    print(f"บิล {total['bills']} · บรรทัด {total['lines']} · "
          f"ซ้ำ(ข้าม) {total['skipped_dup']} · แท็บที่ข้าม {total['skipped_tab']}")
    if vendors:
        print(f"\nร้านใหม่ที่จะถูกสร้าง ({len(vendors)}): {', '.join(vendors[:20])}")
    if issues:
        print(f"\nแถวที่ข้าม ({len(issues)}):")
        for i in issues[:25]:
            print(f"  {i['tab']}!แถว{i['row']}: {i['reason']}")
        if len(issues) > 25:
            print(f"  ... อีก {len(issues) - 25} รายการ")

    print("\n--- ตรวจทานยอดต่อคัน (ชีท vs ระบบ) ---")
    bad = 0
    for tab, sheet_net, sys_net in recon:
        diff = round(sheet_net - sys_net, 2)
        flag = "OK " if abs(diff) <= 0.01 else "MISMATCH"
        if abs(diff) > 0.01:
            bad += 1
        print(f"  {flag} {tab:<22} ชีท {sheet_net:>14,.2f}   ระบบ {sys_net:>14,.2f}   ต่าง {diff:>10,.2f}")
    print(f"\nไม่ตรง {bad} คัน จาก {len(recon)} คัน")
    if bad:
        print("!! ยอดไม่ตรง — ถ้าเพิ่ง --apply ให้ rollback แล้วแก้ก่อน")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, choices=[*rmi.SHEETS, "all"])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()

    slugs = list(rmi.SHEETS) if a.file == "all" else [a.file]
    if a.rollback:
        with Session(engine) as s:
            for slug in slugs:
                n = rmi.rollback_file(s, slug, dry_run=True)
                print(f"{slug}: จะลบ {n} บิล (พร้อมบรรทัดลูก)")
                if n and (a.yes or input("พิมพ์ 'yes' เพื่อลบจริง: ") == "yes"):
                    print(f"  ลบแล้ว {rmi.rollback_file(s, slug, dry_run=False)} บิล")
        return
    for slug in slugs:
        run(slug, apply=a.apply)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: รัน dry-run กับชีทจริง (ยังไม่เขียน DB)**

```bash
cd "Project YK" && ProjectYK_System/app/.venv/Scripts/python.exe -X utf8 ProjectYK_System/tools/import_rm_history.py --file lcb
```
คาด: พิมพ์จำนวนบิล ≈ 3,051 · รายชื่อแท็บที่ข้าม · รายชื่อร้านใหม่ · ตาราง "ตรวจทานยอด" ที่ระบบยังเป็น 0
(dry-run ไม่เขียน จึงเทียบยอดไม่ได้ — ค่าจากคอลัมน์ `system_net` คือ "ยอดที่จะเข้า" ใช้เทียบได้เลย)

- [ ] **Step 3: ให้โอดูรายงาน issues ก่อน แล้วค่อย commit**

```bash
git add ProjectYK_System/tools/import_rm_history.py
git commit -m "feat(rm-history): CLI dry-run/apply/rollback + ตรวจทานยอดต่อคัน"
```

---

### Task 5: import จริง ทีละไฟล์ + ตรวจทาน

- [ ] **Step 1: สำรอง DB บน server ก่อนแตะเงิน**

```bash
ssh yklog@100.97.150.114 "Copy-Item 'C:\Users\yklog\YK_MVP\app\app.db' \"C:\Users\yklog\YK_MVP\app\app.db.bak_before_rm_$(Get-Date -Format yyyyMMdd_HHmmss)\""
```

- [ ] **Step 2: `--apply` ไฟล์แรก (lcb) บน dev ก่อน แล้วดูตารางตรวจทาน**

```bash
ProjectYK_System/app/.venv/Scripts/python.exe -X utf8 ProjectYK_System/tools/import_rm_history.py --file lcb --apply
```
เกณฑ์ผ่าน: **ไม่ตรง 0 คัน** — ถ้าไม่ผ่าน `--rollback --file lcb --yes` แล้วแก้ parser

- [ ] **Step 3: ทำซ้ำกับ wangnoi และ bigc**

- [ ] **Step 4: ชุดเต็ม + deploy DB ที่ import แล้ว (หรือรันสคริปต์บน server ตรงๆ)**

```bash
cd ProjectYK_System/app && .venv/Scripts/python.exe -X utf8 -m pytest -q -p no:cacheprovider
```

- [ ] **Step 5: Commit changelog**
