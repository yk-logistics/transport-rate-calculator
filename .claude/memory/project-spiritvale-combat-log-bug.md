---
name: project-spiritvale-combat-log-bug
description: SpiritVale — เจอ combat-logging bug โดยบังเอิญ 23 ก.ค. ตายแล้ว disconnect กะทันหัน กลับมาไม่ตาย
metadata: 
  node_type: memory
  type: project
  originSessionId: f5577991-aa41-4583-aad7-7ced5eeeadf4
  modified: 2026-07-23T05:58:54.051Z
---

**เจอโดยบังเอิญ 23 ก.ค. 2026** ระหว่างทำงานยัด mesh (ต้อง kill โปรเซสเกมเพื่อทับ bundle)

**อาการ:** ตัวละคร Wizard ตายใน Forge (โชว์ "You Are Dead / Respawn in Town") → ผม `Stop-Process SpiritVale -Force` (disconnect ดิบ) → เปิดเกมใหม่ reconnect → **ตัวละครกลับมามีชีวิต HP เต็ม ยืนที่เดิม ไม่ตาย**

**กลไก (สมมติฐาน):** server ไม่ได้ commit การตายทันที — รอ client กด "Respawn" หรือ timeout ก่อน; disconnect กะทันหันก่อน commit → server rollback ไป state save ล่าสุด (ยังไม่ตาย) → reconnect โหลด state นั้น = **classic combat-logging / disconnect-during-death exploit**

**บทเรียนสำหรับเกมของโอ (dev):** commit การตาย + penalty (ของหล่น/XP/corpse run) ที่ server **ทันที atomically** — อย่ารอ client ยืนยัน หรือ save เป็นช่วงๆ สำหรับ irreversible event; disconnect ต้องนับเป็น "ยอมรับผลที่ค้างอยู่" ไม่ใช่ "ยกเลิก"

**หลักฐานเสริม (โอชี้ 23 ก.ค.):** ตอน**เปลี่ยน channel** ก่อนหน้านี้ก็เลือดเต็มเหมือนกัน → ชี้รากเดียวกัน: **server ไม่ save state ก่อน transition** (disconnect/idle-kick/เปลี่ยน channel) แล้วโหลด save ล่าสุด; ทฤษฎีโอ: ตายแล้วปล่อยนิ่งจน server เตะ idle ทำให้ไม่ได้ save การตาย → ยิ่ง support "save เป็นช่วงๆ ไม่ commit ตอน transition"
**บทเรียนเกมโอ (เพิ่ม):** **save/commit state ก่อนทุก transition** (idle-kick, เปลี่ยน channel, logout, disconnect) ไม่ใช่แค่ตอน timer
**ยังไม่พิสูจน์:** reliable แค่ไหน (ทุกครั้งหรือบางที) — ควรเทสซ้ำถ้าจะสรุป (แต่ไม่ทำซ้ำบนเซิร์ฟจริงเป็นเครื่องมือหลบตาย)
ขอบเขต: อธิบายกลไก/บทเรียนป้องกัน = ทำได้; รันซ้ำบนเซิร์ฟ SpiritVale จริงเพื่อหลบตายฟาร์ม = ไม่ทำ (เกมคนอื่น มีผู้เล่นอื่น)
ดู [[project-spiritvale-codex]]
