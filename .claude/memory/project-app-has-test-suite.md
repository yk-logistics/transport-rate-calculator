---
name: project-app-has-test-suite
description: แอปมี pytest suite จริง 545 tests ที่ ProjectYK_System/app/tests/ (CLAUDE.md เคยบอกผิดว่าไม่มี — แก้แล้ว 8ก.ค.)
metadata: 
  node_type: memory
  type: project
  originSessionId: cc086771-bff3-4262-a48c-795610894992
---

**8 ก.ค. 2026** — CLAUDE.md เดิมบอก "ไม่มี test suite / linter" แต่จริงมี **pytest suite 545 tests** ที่ `ProjectYK_System/app/tests/` (118 ไฟล์, pytest 9.1.1) แก้ CLAUDE.md ให้ตรงแล้ว

**รันยังไง** (จาก `ProjectYK_System/app/`):
```
.venv/Scripts/python.exe -X utf8 -m pytest -q -p no:cacheprovider          # ทั้งชุด
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_xxx.py -q            # ไฟล์เดียว
```
- `conftest.py` บังคับ throwaway SQLite (env `DATABASE_URL`) + `YK_INSECURE_COOKIES=1` + drop/create schema ต่อ test → รันได้เลยไม่แตะ DB จริง
- ต้อง `-X utf8` / `PYTHONIOENCODING=utf-8` เสมอ ไม่งั้น console Windows (cp1252) encode ข้อความไทยใน test พังกลางคัน
- ไม่มี `pytest-timeout` (อย่าใช้ `--timeout`); ไม่มี linter
- **ยังไม่ทดแทน preflight** — งานเงิน/import ยังต้องผ่าน preflight scripts ใน tools/ เพิ่ม (กฎเงินเดิม)

**Warning ค้าง (ไม่ใช่บั๊ก):** SAWarning FK cycle `maintrecord ↔ pmplan` ตอน DROP (MaintRecord.pm_plan_id ↔ PmPlan.last_maint_record_id อ้างกันไปมา) — เกิดแค่ตอน test cleanup, prod ไม่ DROP ไม่กระทบ; แก้ต้องใส่ use_alter=True ที่ FK แต่แตะ models เลยเว้นไว้

เกี่ยว: งานแก้ driver cookie secure ([[reference-payroll-close-runbook]] คนละเรื่อง) ใช้ suite นี้ TDD จริง
