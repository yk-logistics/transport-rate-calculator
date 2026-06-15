# Cowork Setup Guide — Project YK

วันที่ setup: 2026-05-19 (Pongsakan)

## ✅ ทำไปแล้ว (ฉันเตรียมให้)

- ✓ CLAUDE.md bootstrap guide — บอกว่าต้องอ่านไฟล์อะไร
- ✓ MODULE_REGISTRY — ดัชนีโมดูลทั้งหมด
- ✓ AI_CURSOR_CLAUDE_WORKFLOW — กิจกรรม Cursor ↔ Claude Code
- ✓ Lean prompt templates — ประหยัดโทเค็น

## 🎯 ต้องทำต่อ (ให้คุณรัน PowerShell บน Windows)

### 1️⃣ Setup `rtk` (Runtime Toolkit)
เปิด **PowerShell as Admin** แล้วรัน:
```powershell
rtk init -g
```
จากนั้น **restart Cowork app** เพื่อให้ hook ทำงาน

### 2️⃣ Setup `claude-mem` Plugin ใน Claude Code
เปิด **Code tab** ใน Cowork แล้วพิมพ์:
```
/plugin marketplace add thedotmack/claude-mem
/plugin install claude-mem@thedotmack
/reload-plugins
```

### 3️⃣ Graphify Code Index (ครั้งแรก)
ใน **Code tab** พิมพ์:
```
/graphify .
```
(ตัว Claude จะขอ permission รัน PowerShell — เห็นคำอธิบายแล้วกด Yes ได้)

---

## 📝 Prompt Templates (พร้อมใช้ — copy-paste)

### **Mode 1: ULTRA-LEAN** (5 บรรทัด)
ใช้เมื่องานเล็กขอบเขตชัด:
```
Token mode: ULTRA-LEAN.
Read only AGENT_BOOTSTRAP.md + MODULE_REGISTRY.md, then jump straight to target code.
Do not read long docs unless blocked; if blocked, read only latest tail section.
Keep scope to exactly one small task; avoid unrelated scans.
[YOUR TASK HERE]
```

### **Mode 2: LEAN** (สมดุล)
ใช้เมื่องานกลาง:
```
You are working in Project YK. Use LEAN token mode.
Task scope: [YOUR TASK — 1-3 lines]

Rules:
- Initial reads only: ProjectYK_System/AGENT_BOOTSTRAP.md, ProjectYK_System/MODULE_REGISTRY.md
- Then go directly to relevant code in ProjectYK_System/app/
- Read CHANGELOG/CONTEXT/NEXT_ACTION only if blocked, latest tail only
- Do not scan unrelated modules

Output:
1) changed files + purpose
2) verification commands + outcomes
3) risks/open questions (max 3)
4) next smallest step
```

### **Mode 3: FULL** (งานหนัก/เงิน)
ใช้เมื่อแตะเงิน, import, payroll:
```
Full context mode — read all bootstrap docs before proceeding.
Task: [YOUR TASK]
Scope/Constraints: [อะไรห้าม]
Preflight verification needed: [ต้องเช็คอะไรก่อนลง]
```

---

## 🚀 วิธีใช้ Code Tab

**เปิด Code tab** ใน Cowork → พิมพ์:

**ตัวอย่างเมื่องานเล็ก:**
```
Token mode: ULTRA-LEAN.
Read only AGENT_BOOTSTRAP.md + MODULE_REGISTRY.md, then jump straight to target code.

Task: แก้ bug ใน DailyJob model — column `fuel_cost` ต้องแสดง 2 ทศนิยมเสมอ

Do not read long docs unless blocked.
Output: changed files + verify + 1 next step.
```

**ตัวอย่างเมื่องานกลาง:**
```
You are working in Project YK. Use LEAN token mode.
Task scope: เพิ่ม validation ใน payroll form เพื่อป้องกัน negative values

Rules: อ่าน bootstrap → ไปเข้าโค้ด → อ่าน NEXT_ACTION_PLAN เฉพาะตอน block
Output: files changed + verify + risks + next step
```

---

## 📚 Reference Files (ใน Code tab ใช้ `@ไฟล์` ได้)

```
@ProjectYK_System/AGENT_BOOTSTRAP.md
@ProjectYK_System/MODULE_REGISTRY.md
@ProjectYK_System/CLAUDE.md
@ProjectYK_System/AI_CURSOR_CLAUDE_WORKFLOW.md
@ProjectYK_System/TransportRateCalculator/docs/NEXT_ACTION_PLAN.md
```

---

## 💡 Tips

1. **งานเล็ก** → ใช้ ULTRA-LEAN (5 บรรทัด)
2. **งานกลาง** → ใช้ LEAN (สมดุล)
3. **งานเงิน/import** → ใช้ FULL + preflight check
4. **ไม่ต้องคัดลอก prompt** — พิมพ์ตรงใน Code tab
5. **ใช้ `rtk` commands** — `rtk git status`, `rtk pytest` เมื่อต้องการดึง output กระทัดรัด

---

## ✅ Checklist Setup

- [ ] รัน `rtk init -g` บน PowerShell (Admin)
- [ ] Restart Cowork
- [ ] เปิด Code tab → ติดตั้ง claude-mem plugin
- [ ] รัน `/graphify .` เพื่อ index code
- [ ] ลองใช้ ULTRA-LEAN prompt ครั้งแรก

---

**เสร็จแล้ว! พร้อมใช้ Cowork + ประหยัดโทเค็น** 🎯
