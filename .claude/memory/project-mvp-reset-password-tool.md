---
name: project-mvp-reset-password-tool
description: "เครื่องมือกู้รหัส MVP: โอเข้า AnyDesk ดับเบิลคลิก RESET_PASSWORD.bat บน Desktop เซิร์ฟเวอร์ เลือก user ได้รหัสชั่วคราว"
metadata: 
  node_type: memory
  type: project
  originSessionId: afc9f978-5a25-4d9c-9701-35beb33d2e9e
---

DONE+deployed 2 ก.ค. 2026 (commit 984728c): โอขอระบบ "ลืมรหัส" ที่ทำเองได้ — เลือกแบบเครื่องมือบนเซิร์ฟเวอร์แทน recovery codes/email (ไม่แตะแอปสักบรรทัด ไม่เปิดช่องเว็บใหม่)

- **ใช้งาน:** AnyDesk เข้าเซิร์ฟเวอร์ → ดับเบิลคลิก `C:\Users\yklog\Desktop\RESET_PASSWORD.bat` → เลือกหมายเลข user → ได้รหัสชั่วคราว 10 ตัว → ล็อกอินแล้วโดนบังคับตั้งรหัสใหม่ (must_change_pw=1) → มีถาม y/n รีสตาร์ทแอปล้างตัวล็อก 15 นาที
- โค้ด repo: `ProjectYK_System/tools/reset_password.py` (สำเนา live: `YK_MVP\app\reset_password.py`); runbook: `ProjectYK_System/docs/MVP_ADMIN_RECOVERY_RUNBOOK.md` (มีแผนสำรอง SSH มือ)
- ทดสอบจริง: สร้าง user `cctest` บนเซิร์ฟเวอร์ → รีเซต → login live 303→/account/password → ลบทิ้งด้วย id แล้ว
- **GOTCHA:** แอปเซิร์ฟเวอร์รันด้วย venv `YK_MVP\app\.venv` (Get-Process โชว์ path เป็น global python เพราะ venv redirector — global python **ไม่มี bcrypt** อย่าใช้); spec: docs/superpowers/specs/2026-07-02-password-recovery-codes-design.md (ชื่อไฟล์ยังเป็น recovery-codes แต่เนื้อในคือดีไซน์นี้); ห้ามทำหน้าเว็บ localhost-trust เพราะ cloudflared ส่งทราฟฟิกนอกมาเป็น 127.0.0.1
- เกี่ยวข้อง: [[project-mvp-password-db-swap-gotcha]] (สาเหตุที่โอโดนล็อกเอาต์ + กฎ preserve appuser ตอน swap DB), [[feedback-no-ai-dependency]]
