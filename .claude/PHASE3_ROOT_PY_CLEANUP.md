# เฟส 3 — ย้าย .py หลุดที่ราก repo (handoff สำหรับ session ใหม่)

> สร้างเมื่อ 2026-06-08 ปิดท้าย session จัดระเบียบ repo (เฟส 1+2 เสร็จ)
> งานเฟส 3 = **โซนเงิน/import/payroll → ใช้โหมดรอบคอบเต็มรูปแบบ, ห้ามเดา** (กฎ CLAUDE.md)

## สถานะที่ทำเสร็จแล้ว (เฟส 1+2)
- ✅ เฟส 1: `git worktree prune` ลบ worktree เก่า stale 8 อัน + ลบ `.claude/worktrees/` + `__pycache__/`
- ✅ เฟส 2: ย้ายของไม่เกี่ยว YK ออกนอก repo → `../_NonYK_Projects/`
  - `makcu/` = makcu_*.py + macro_engine.* + macros.json + test_macro_combined.py + _make_shortcut.ps1 (16 ไฟล์, untracked)
  - `valorant/` = อดีต `Delete/unrelated_valorant/` (**เคย tracked → git มี 5 deletions ค้าง ยังไม่ commit**)

## เฟส 3 — งานที่เหลือ: ย้าย .py 14 ตัวที่ราก repo

### ⚠️ ต้องให้โอ confirm ก่อนแตะ
1. **ปลายทางคือไหน?** root มีทั้ง `tools/` และ `ProjectYK_System/tools/` — ต้องรู้ว่าใช้ตัวไหน (CLAUDE.md ระบุ import CLI = `ProjectYK_System/tools/`)
2. **ตัวไหน "ยังใช้" (→ tools/) ตัวไหน "เลิก/รอบเดียว" (→ `Delete/candidates_you_move_here/`)** — โอเท่านั้นที่รู้

### ตาราง 14 ไฟล์ (จาก recon: นับ path/cwd refs)
| ไฟล์ | refs | tracked? | เดาปลายทาง | โอ: ใช้/เลิก? |
|---|---|---|---|---|
| compute_lcb_payroll.py | 🔴3 | untracked | เงิน — รอบคอบ | ? |
| payroll_system.py | 🔴3 | tracked | เงิน — อาจซ้ำ app/services/payroll.py? | ? |
| import_lcb_fuel.py | 🔴3 | untracked | import — รอบคอบ | ? |
| import_lcb_may2026.py | 🔴3 | untracked | ชื่อ one-shot (พ.ค.) → Delete? | ? |
| reimport_lcb_daily.py | 🔴3 | untracked | import — รอบคอบ | ? |
| analyze_bigc_revenue.py | 🟡1 | tracked | tools/ | ? |
| check_fuel.py | 🟡1 | tracked | tools/ | ? |
| generate_logbook_excel.py | 🟡1 | tracked | tools/ | ? |
| generate_demurrage_customer_letter_docx.py | 🟡1 | tracked | tools/ | ? |
| split_sheets_to_csv.py | 🟡1 | tracked | tools/ | ? |
| calc_trip_hours.py | 🟢0 | tracked | tools/ | ? |
| check_outstanding_apr26.py | 🟢0 | tracked | ชื่อ one-shot (เม.ย.) → Delete? | ? |
| create_letter.py | 🟢0 | tracked | tools/ | ? |
| generate_quotation.py | 🟢0 | tracked | tools/ | ? |

### Path deps (qwen recon + Opus verified 2026-06-08)
- **อ้าง `C:\Users\Home\...` (เครื่องเก่า → รันไม่ได้แล้ว, one-shot):** analyze_bigc_revenue, check_outstanding_apr26, create_letter, split_sheets_to_csv, import_lcb_fuel, import_lcb_may2026, reimport_lcb_daily → ทิ้ง `Delete/` ได้ (ถ้าโอยืนยันเลิกใช้)
- **`__file__`/cwd-based ย้ายเข้า tools/ ปลอดภัย:** calc_trip_hours (no I/O), check_fuel, generate_demurrage_customer_letter_docx, generate_logbook_excel, generate_quotation
- **payroll_system.py:** `__file__`-based + อ่าน/เขียน `name_memory.json`+`column_memory.json`+`clean_name_memory.json`+`price_memory.json` ใน dir เดียวกัน → **ย้าย 4 json ไปด้วยเสมอ**
- **compute_lcb_payroll.py:** `SCRIPT_DIR/"ProjectYK_System"/"app"/"app.db"` + `sys.path.insert(SCRIPT_DIR/ProjectYK_System/app)` → ย้ายเข้า `ProjectYK_System/tools/` ต้องแก้เป็น `SCRIPT_DIR.parent/"app"/...`

### กฎลงมือเฟส 3
- **5 ไฟล์แดง (เงิน):** เปิดอ่าน path ก่อนย้าย → ถ้าใช้ relative-from-root ต้องแก้เป็น `__file__`-based หรือ absolute → verify **ด้วย `py_compile` เท่านั้น** (รันจริง = แตะ DB ห้ามทำ)
- tracked → `git mv`; untracked → `mv` ปกติ
- ย้ายเสร็จทุกกลุ่ม verify: `py_compile` ผ่าน + `start.bat` แอปยังรันได้
- หลังจบทั้งหมด: รวบ commit (รวม valorant deletion) แบบ surgical — branch ก่อน (main มี remote)

## อัปเดต 2026-06-08 (ทำต่อใน session เดิม — qwen ช่วย recon)
- ✅ ย้าย 7 ไฟล์ Home-path (เครื่องเก่า, รันไม่ได้แล้ว) → `Delete/candidates_you_move_here/` — committed
- ✅ ย้าย `payroll_system.py` + 5 json (name/name_backup/column/clean_name/price_memory) + `compute_lcb_payroll.py` → `Delete/` — committed (เก่า/ถูกแทนด้วยเว็บ; engine จริงอยู่ app/services/payroll.py)
- งาน cleanup เฟส 1-3(บางส่วน) = 3 commits, merge เข้า main แล้ว

### เหลือทำ (session หน้า): 5 utility ที่ root — ปลอดภัยย้าย (__file__/cwd-based)
`calc_trip_hours.py`, `check_fuel.py`, `generate_demurrage_customer_letter_docx.py`, `generate_logbook_excel.py`, `generate_quotation.py`
- decide: ย้ายเข้า tools/ ไหม + **ยืนยันปลายทาง** (`tools/` ราก หรือ `ProjectYK_System/tools/`?)
- ทั้ง 5 ยังดูใช้งานอยู่ (ออกใบเสนอราคา/logbook/จดหมาย demurrage/คิดชั่วโมง/เช็คน้ำมัน) — ถามโอก่อนว่าตัวไหนยังใช้

## เริ่ม session ใหม่ยังไง
สั่ง CC: *"อ่าน `.claude/PHASE3_ROOT_PY_CLEANUP.md` แล้วทำเฟส 3 ต่อ"*
