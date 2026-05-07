# Claude Code Lean Prompt Template (Project YK)

Template นี้ใช้เพื่อลด token สำหรับงานที่ **scope เล็กและชัดเจน** โดยยังคุมความเสี่ยงพื้นฐาน

## ใช้เมื่อไหร่

- แก้ 1 ฟีเจอร์ย่อย / 1 bug / 1 guardrail
- ไม่ใช่งาน import/payroll ที่กระทบตัวเงินจำนวนมาก
- ไม่ใช่งานที่ต้องทบทวนทั้งระบบ

## Prompt (copy-paste)

```text
You are working in Project YK. Use LEAN token mode.

Task scope:
- [ใส่งานสั้นๆ 1-3 บรรทัด]

Token policy:
- Do NOT read long docs first.
- Initial reads allowed only:
  1) ProjectYK_System/AGENT_BOOTSTRAP.md
  2) ProjectYK_System/MODULE_REGISTRY.md
- Then read only code files directly related to this task.
- Read CHANGELOG_MASTER / CONTEXT_LOG / NEXT_ACTION only if blocked, and only latest tail section.
- Do not scan unrelated modules.

Safety policy:
- If ambiguity affects money/data integrity, stop and ask max 3 questions.
- Keep changes small and reversible.

Output format:
1) What changed (files + purpose)
2) Verification commands + outcomes
3) Remaining risks/open questions (max 3)
4) Recommended next step
```

## Fast variants

### Variant A: tiny UI tweak

- ข้าม docs เพิ่มเติมทั้งหมดหลังอ่าน 2 ไฟล์แรก
- อ่านเฉพาะ template + route ที่เกี่ยว

### Variant B: backend logic tweak (ไม่แตะเงิน)

- อ่านเฉพาะ service/route/model ที่เกี่ยว
- บังคับรัน test/verify เฉพาะโมดูลที่แก้

## ห้ามใช้ Lean

- งาน import/payroll/recompute/finalize
- งาน reconcile ยอดเงิน หรือมีความเสี่ยงข้อมูลตกหล่น
- งานข้ามหลายโมดูลที่มี dependency สูง
