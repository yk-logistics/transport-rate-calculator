# CC Auto Two-Agent Runbook (Windows + Cursor)

คู่มือนี้สำหรับโหมดที่ต้องการให้ Claude Code ทำงานแบบ 2 บทบาท:

- **Agent A (Coordinator)**: คุมคุณภาพ/คุมสโคป/ตัดสินใจรอบถัดไป
- **Agent B (Executor)**: ลงมือแก้จริง/รัน verify/recompute แล้วส่งตัวเลขกลับ

> เป้าหมาย: ลด copy-paste, ลด token waste, และกัน scope หลุด

## ก่อนเริ่ม (เช็กครั้งเดียว)

1. เปิด Cursor ที่รากโปรเจกต์ `Project YK`
2. เปิด Terminal 2 หน้าต่างใน Cursor
3. ทั้งสองหน้าต่าง `cd` ไปที่:
   - `C:\Users\Home\Desktop\Project YK`
4. รัน `cc` ทั้งสองหน้าต่าง (จะได้ 2 session แยกกัน)
5. ตั้งชื่อในใจ:
   - Terminal A = Coordinator
   - Terminal B = Executor

## ขั้นตอนใช้งานจริง (ทีละขั้น)

### Step 1) ยิง prompt เริ่มต้นให้ Agent A (Coordinator)

วางใน Terminal A:

```text
You are Coordinator (read-only).
Do not edit code.
Your job is quality gate + scope control for Project YK payroll/import checks.

For each round, output only:
1) status of 4 checks (unlinked / cycle tag / cross-site collision / source mismatch)
2) highest-risk issue
3) exactly one single-scope task card for Executor
4) max 3 clarification questions only if money correctness is ambiguous

Keep concise and numeric.
Default site order: BigC -> LCB -> AYU.
```

### Step 2) ให้ Agent A ออก "Task Card #1"

ใน Terminal A พิมพ์:

```text
Create Task Card #1 for BigC only, single scope, safe-first.
```

### Step 3) ส่ง Task Card #1 ให้ Agent B (Executor)

คัดลอกเฉพาะ Task Card แล้ววางใน Terminal B พร้อม prefix นี้:

```text
Execute this task card exactly. Single scope only.
If blocked by ambiguity affecting money, ask max 3 questions.
Output:
1) changed files
2) what changed
3) before/after numbers
4) remaining risks (count + amount)
5) proposed next task card title
```

### Step 4) ส่งผลจาก B กลับให้ A สรุป

เมื่อ B ตอบจบ ให้คัดลอกผลสรุป (ไม่ต้องคัดทั้ง log ยาว) ไปให้ A:

```text
Executor result for review:
[paste short result]

Do quality gate now and generate Task Card #2.
```

### Step 5) วนลูปซ้ำ

- A ออก Task Card ถัดไป
- B ลงมือทำตามการ์ดเดียว
- ส่งผลกลับ A
- ทำซ้ำจน A สรุปว่า pass ครบ 4 checks

## กติกากันพัง (สำคัญ)

1. **หนึ่งรอบ = หนึ่ง scope เท่านั้น**
2. B ห้าม refactor กว้างเอง
3. ถ้ากำกวมเรื่องเงิน: หยุดถามก่อน ไม่เดา
4. ทุกรอบต้องมีตัวเลข before/after
5. ยังห้าม finalize payrun ถ้า A ยังไม่ให้ผ่าน

## รูปแบบ Task Card (มาตรฐาน)

ให้ Agent A ออกการ์ดแบบนี้ทุกครั้ง:

```text
Task Card #[N]
Site/Cycle: [example BIGC 2026-02]
Scope: [single scope]
Why: [risk + amount]
Do:
- step 1
- step 2
Verify:
- query/command 1
- query/command 2
Pass condition:
- numeric condition
Out of scope:
- explicit no-touch list
```

## วิธีประหยัด Token แบบใช้จริง

1. ใช้ข้อความสั้นในแต่ละรอบ (ไม่เล่า narrative ยาว)
2. ส่งเฉพาะสรุปผลจาก B กลับ A
3. ให้ A สรุปแค่ pass/fail + task card ถัดไป
4. ถ้าใกล้ reset quota:
   - ให้ A ออก "handoff snapshot" 8-12 บรรทัด
   - เปิด session ใหม่แล้ววาง snapshot ต่อได้ทันที

## Handoff Snapshot (กัน context หลุด)

ก่อนปิด session ให้ A สร้าง snapshot รูปแบบนี้:

```text
Round Snapshot
- Current site/cycle:
- Completed task cards:
- Latest before/after:
- Remaining risks (count + amount):
- Next task card:
- Blocking questions (if any):
```

## บันทึกเก็บไว้ใช้ซ้ำ

ทุกครั้งที่จบรอบใหญ่ ให้บันทึก 3 อย่าง:

1. อัปเดต `ProjectYK_System/TransportRateCalculator/docs/CONTEXT_LOG.md`
2. อัปเดต `ProjectYK_System/TransportRateCalculator/docs/NEXT_ACTION_PLAN.md`
3. เก็บ prompt ล่าสุดที่เวิร์คไว้ท้ายไฟล์นี้ (section "Working Prompts")

## Working Prompts (เติมได้เรื่อยๆ)

### Coordinator quick prompt

```text
Quality gate this executor result.
Return: pass/fail for 4 checks, biggest remaining risk, next single-scope task card.
```

### Executor quick prompt

```text
Implement only this task card. Recompute. Return before/after + residual risk count/amount.
```

