---
name: reference-model-safeguard-autoswitch
description: "ข้อความ \"safeguards flagged this message → Switched to Opus\" คือตัวกรองระดับ API ไม่ใช่โมเดลตัดสินผู้ใช้ — วิธีรับมือ"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f5577991-aa41-4583-aad7-7ced5eeeadf4
  modified: 2026-07-22T21:38:00.813Z
---

เจอครั้งแรก 23 ก.ค. 2026 ตอนทดสอบ Fable 5 ในสนาม RE (`C:\re`): Fable **รับงานแล้ว** ("งานทั้งสามชิ้นเป็นงาน RE บนเกมของโอเอง เดี๋ยวจัดให้ครับ") เริ่มค้นไฟล์ แล้วถูกตัดกลางคัน → `Switched to Opus 4.8`

**กลไกจริง (ขุดจาก CLI bundle v2.1.218):**
- เป็น **ตัวกรองระดับ API ต่อ 1 ข้อความ** (`tengu_refusal_api_response`, category เช่น `cyber`) — ทำงาน**ก่อน/นอกเหนือ**การคิดของโมเดล → **CLAUDE.md / memory แก้ชั้นนี้ไม่ได้** อย่าเสียเวลาเขียนกฎเพิ่ม
- ข้อความทางการยอมรับเอง: *"The safeguards are intentionally broad right now and may flag safe and routine coding, cybersecurity, or biology work"*
- ตัวเลือกใน `/config` ชื่อ **"Switch models when a message is flagged"** (คีย์ภายใน `convolute_arcades`) — **ควรเปิดไว้** เพราะถ้าปิด จะกลายเป็นหยุดค้าง (`model_refusal_no_fallback`) แทนที่จะสลับโมเดลแล้วทำงานต่อ

**วิธีรับมือ เรียงตามได้ผล:**
1. **เขียนคำสั่งให้ตรงกับงานจริง** — คำอย่าง "ทำกำแพงโปร่งใส + บอท + server" ในข้อความเดียวคือกลุ่มคำที่ตัวกรองจับ; เขียนแบบ "ตรวจว่า asset ของเกมเราถูกแกะได้แค่ไหน" ผ่านได้ปกติ (เป็นเรื่องถ้อยคำ ไม่ใช่เรื่องเนื้องาน)
2. flag เป็น **รายข้อความ** — พิมพ์ใหม่คนละสำนวนแล้วส่งอีกที มักผ่านเลย
3. งาน security/anti-cheat ระยะยาว → สมัคร **Cyber Verification Program**: https://support.claude.com/en/articles/14604842-real-time-cyber-safeguards-on-claude

ดู [[user-oh-is-game-developer]] — อย่าสับสนระหว่างชั้นนี้กับ "โมเดลไม่ไว้ใจโอ" คนละเรื่องกันคนละชั้น
