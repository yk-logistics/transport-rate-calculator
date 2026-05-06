# Claude Code Vibecoding Playbook (BigC -> LCB -> AYU)

เอกสารนี้ออกแบบให้โอคุยกับ Cursor เป็นภาษาไทย แล้วให้ Cursor สรุปเป็น prompt อังกฤษแบบสั้น-คมเพื่อส่งต่อ Claude Code โดยไม่เปลืองโทเค็น

## 1) Working Contract (ใช้ทุกงาน)

- เป้าหมาย: ทำงานจริง, ลดเดา, ตรวจรั่วข้อมูลการเงินก่อนสรุป
- ลำดับไซต์รายเดือน (default): **BigC -> LCB -> AYU**
- ทุกงานที่แตะ import/payroll ต้องมี Preflight + Recompute + Before/After
- ถ้าข้อมูลกำกวม (ชื่อซ้ำ/ไซต์ซ้อน/รอบเดือนวิ่ง-จ่าย): หยุดถามก่อน ไม่เดา

## 2) Definition of Done (DoD) ต่อ 1 งาน

Claude Code ต้องส่งกลับให้ครบ 7 อย่าง:

1. Changed files
2. Business impact (รายการ/ยอดเงินที่กระทบ)
3. Preflight result (4 checks)
4. Recompute result
5. Before vs After (ตัวเลขเทียบ)
6. Risk/remaining gaps
7. Exact verify commands ที่รันแล้ว

## 3) Mandatory Preflight (ทุกไซต์)

ก่อนแก้ logic:

1. **Unlinked records**
   - มีรายการหักที่ยังไม่ผูกคนขับหรือไม่ (`driver_id is null`)
   - ต้องรายงานจำนวนรายการ + ยอดเงินรวม
2. **Cycle tag integrity**
   - แยกเดือนวิ่ง (`work month`) vs เดือนจ่าย (`pay month`) ถูกหรือไม่
3. **Cross-site name collision**
   - ชื่อเดียวกันข้ามไซต์ (เช่น คนขับชื่อซ้ำ) ปนผลคำนวณหรือไม่
4. **Source mismatch**
   - daily/fuel/petty/payroll ใช้แหล่งข้อมูลคนละชุดจนรวมผิดหรือไม่

หลังแก้ logic:

- ต้อง recompute และสรุป Before/After เป็นตัวเลข
- ถ้ายังมีตกหล่นทางเงิน: ระบุจำนวนรายการ + ยอดเงิน + วิธีแก้ทันที

## 4) Site-specific focus

### BigC

- เน้น consistency ของ fuel residual/rebate และรอบจ่ายรายเดือน
- ตรวจการปนข้อมูลข้ามไซต์เป็นอันดับแรก

### LCB

- แยกโหมดรายเที่ยว vs เหมาน้ำมันให้ชัด
- ตรวจรายการ “ไม่แบ่ง” และผลกระทบกับ net pay

### AYU

- ตรวจการันตี + การหักตามวันลา/ขาด
- ตรวจ deduction จาก toll/mflow และความครบถ้วนของ petty linkage

## 5) Token-Saving rules (Claude Code)

1. 1 session = 1 scope เท่านั้น
2. หลีกเลี่ยงอ่านไฟล์ยาวทั้งก้อนไม่จำเป็น
3. ใช้คำสั่งสั้นๆ ที่ให้สัญญาณชัดเจนก่อน (`rtk git status`, `rtk git diff`)
4. แตะเฉพาะไฟล์ที่เกี่ยวกับ scope
5. สรุปผลเป็น bullet สั้นพร้อมตัวเลข ไม่เขียน narrative ยาว
6. ถ้าไม่ชัวร์ ให้ถาม 1-3 คำถามสำคัญก่อนลงมือ

## 6) English Prompt Template (Cursor -> Claude Code)

```text
Task: [short task name]

Context:
- Project: Project YK (FastAPI + SQLModel + SQLite dev)
- Work mode: implement directly, then verify with business-safe checks
- Site order default: BigC -> LCB -> AYU

Scope:
- Files/modules: [exact paths]
- Out of scope: [what must not be touched]

Mandatory checks before and after code changes:
1) unlinked records
2) cycle tag integrity (work month vs pay month)
3) cross-site name collision
4) source mismatch across daily/fuel/petty/payroll

Implementation requirements:
- If any ambiguity impacts money/data correctness, stop and ask max 3 clarification questions.
- Do not guess.
- Apply safe defaults that are traceable.
- After changes, run recompute and provide before-vs-after numbers.
- Report leaked money risk as count + amount and provide immediate fix path.

Output format:
1) changed files
2) what was implemented
3) preflight results (with numbers)
4) recompute + before/after
5) remaining risks
6) verification commands run
```

## 7) Quick Prompt Pack (copy-ready)

### A) Payroll logic fix

```text
Fix payroll logic for [SITE] [CYCLE_TAG].

Do preflight first:
- unlinked petty rows (count + amount)
- cycle tag integrity
- cross-site name collisions
- source mismatch daily/fuel/petty/payroll

Then implement the fix in code, recompute payroll, and report before/after totals (gross, deductions, net).
If ambiguity affects money, ask up to 3 clear questions before coding.
```

### B) Import hardening

```text
Harden import pipeline for [SITE] [MONTH].
Add/adjust guards so no silent data leaks happen for:
- unlinked driver records
- wrong cycle tags
- cross-site name collisions
- source mismatch

Provide preflight report with numeric impact, then implement and re-run import verification.
```

### C) Billing/summary validation

```text
Validate billing/payroll consistency for [SITE] [CYCLE_TAG].
Cross-check daily, fuel, petty, and payroll aggregates.
Show mismatch list with count and amount, then implement the minimum safe fix.
Recompute and provide before/after with exact numbers.
```

