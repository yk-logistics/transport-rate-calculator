# ProjectYK System Hub

โฟลเดอร์นี้คือศูนย์กลางเอกสารสำหรับ AI Agent และทีมงาน เพื่อกัน context หลุดเมื่อคุยหลายแชท/หลายระบบ

## เริ่มอ่านจากไฟล์นี้
- `AGENT_BOOTSTRAP.md` - กติกาเริ่มงานของ Agent
- `MODULE_REGISTRY.md` - สารบัญรวมทุกระบบใน Project YK
- `CHANGELOG_MASTER.md` - สรุปการตัดสินใจข้ามระบบ

## แนวคิดการใช้งาน
- เอกสารเชิงลึกยังอยู่ในแต่ละระบบเดิม (เช่น `AccidentCases`, `ProjectYK_System/TransportRateCalculator/docs`)
- โฟลเดอร์นี้ทำหน้าที่เป็น "ดัชนีกลาง + ประวัติกลาง" เท่านั้น

## กติกาเพิ่มระบบใหม่
1. สร้างโฟลเดอร์ระบบใหม่ตามปกติ
2. มีไฟล์ความจำของระบบนั้นอย่างน้อย 2 ไฟล์:
   - `AGENT_MEMORY.md`
   - `DECISION_LOG.md`
3. เพิ่มรายการใน `MODULE_REGISTRY.md`
4. บันทึกการเปลี่ยนแปลงสำคัญใน `CHANGELOG_MASTER.md`

## Automation
ใช้สคริปต์นี้เพื่อลดงาน manual:

`python ProjectYK_System/bootstrap_module.py <module_path> --purpose "<คำอธิบาย>"`

ตัวอย่าง:

`python ProjectYK_System/bootstrap_module.py SalesOps --purpose "งานขายและวางแผนลูกค้า"`

สคริปต์จะสร้าง/อัปเดตอัตโนมัติ:
- `<module_path>/AGENT_MEMORY.md`
- `<module_path>/DECISION_LOG.md`
- `ProjectYK_System/MODULE_REGISTRY.md`
- `ProjectYK_System/CHANGELOG_MASTER.md`

สำหรับ Windows แบบดับเบิลคลิก:

- เปิด `ProjectYK_System/bootstrap_module.bat`
- กรอก `Module path` และ `Purpose`
- ระบบจะเรียก `bootstrap_module.py` ให้อัตโนมัติ
