# CC Benchmark Log (Lean vs Ultra-Lean)

ใช้ไฟล์นี้บันทึกผลการใช้งาน Claude Code เพื่อวัดว่าโหมดไหนคุ้มที่สุดในงานจริง

## วิธีวัด (3 ตัวชี้วัดหลัก)

1. **เวลาเริ่มลงมือ (Time to first code change)**  
   นับจากส่ง prompt จนมีการแก้ไฟล์แรก
2. **โทเค็นที่ใช้ (Token used)**  
   เอาค่าที่เห็นจาก CC/usage panel หลังจบงาน
3. **จำนวนรอบถามกลับ (Clarification rounds)**  
   จำนวนครั้งที่ CC หยุดถามก่อนลงมือ

## กติกาเก็บข้อมูล

- งานเล็กให้เริ่มจาก `CC_ULTRA_LEAN_5LINES.txt` ก่อนเสมอ
- ถ้าเกิน 1 รอบถามกลับหรือเริ่มช้าเกิน 10 นาที ให้ขยับไป `CC_LEAN_START.txt`
- งานที่กระทบเงิน/import/payroll **ไม่ใช้ Ultra-Lean**

---

## Baseline Template (copy ต่อรอบ)

### Run #<id> - <YYYY-MM-DD HH:mm>
- Task:
- Scope type: `tiny-ui` | `small-backend` | `money-critical`
- Prompt mode: `ultra-lean` | `lean` | `careful`
- Time to first code change (min):
- Token used:
- Clarification rounds:
- Outcome: `pass` | `partial` | `fail`
- Notes:

---

## Decision Rule (หลังครบ 3-5 run)

- ถ้า `ultra-lean` ชนะชัดเจน (เร็วกว่าและถามกลับน้อยกว่า) ให้คงเป็น default งานเล็ก
- ถ้า `ultra-lean` fail หรือถามกลับบ่อย ให้ default เป็น `lean`
- ถ้างานเข้ากลุ่มเงิน ให้บังคับ `careful` ทันที
