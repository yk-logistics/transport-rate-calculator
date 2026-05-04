# TransportRateCalculator Docs

เอกสารในโปรเจกต์ถูกจัดกลุ่มให้อ่านง่ายขึ้นในโฟลเดอร์นี้

## Core Docs

- `MASTER_SPEC.md` - ข้อกำหนดระบบรวมทั้งองค์กร
- `ROLE_MATRIX.md` - หน้าที่และสิทธิ์ผู้ใช้งาน
- `DEPLOYMENT_FREE_WINDOWS.md` - แนวทางติดตั้งฟรีบน Windows + Tailscale
- `DAILY_MODULE_DESIGN.md` - แบบร่างโมดูล Daily -> Billing -> Payroll
- `CONTEXT_LOG.md` - บันทึกสรุปการคุยและข้อสรุปแต่ละรอบ
- `NEXT_ACTION_PLAN.md` - แผนงานลำดับถัดไป (อัปเดตต่อเนื่อง)
- `DATA_DICTIONARY.md` - นิยามข้อมูลกลางและ field ระดับตาราง
- `JOB_STATUS_FLOW.md` - สถานะงานและเงื่อนไขเปลี่ยนสถานะ
- `CUSTOMER_BILLING_PROFILE_TEMPLATE.md` - แม่แบบเงื่อนไขวางบิลรายลูกค้า
- `CUSTOMER_BILLING_PROFILES.md` - seed profile ลูกค้าเริ่มต้น
- `ENUMS_AND_RULES.md` - enum กลางของระบบ
- `DATA_LOCK_POLICY.md` - นโยบาย lock/adjust ข้อมูลหลังปิดรอบ
- `API_CONTRACT_V1.md` - สัญญา API สำหรับ MVP
- `SQL_SCHEMA_V1.md` - โครงสร้างฐานข้อมูล PostgreSQL รุ่นแรก
- `IMPORT_MAPPING_SPEC.md` - mapping Excel → DB per site (AYU/BIGC/LCB) จาก Daily.xlsx ตัวอย่างจริง
- `SITE_PAYROLL_RULES.md` - กฎเงินเดือน 3 ไซต์ + deductions ทั้งหมด
- `BIGC_BRANCH_RATE_SPEC.md` - สูตรค่าขนส่ง BIGC (1Big c / 1+ / 2BigC / 2++ / รับรถ / 1DH)
- `WORKFLOW_BY_TEAM.md` - ทีม 7 คน + vision workflow + cross-site scenario

## Existing Reference

- `../COST_MODEL.md` - baseline สูตรต้นทุน
- `../GOOGLE_DRIVE_SYNC_SETUP.md` - วิธีซิงก์ Google Drive
- `../README_DEPLOY.md` - เอกสาร deploy เดิม

## Operating Rule

- ทุกครั้งที่มีการคุยสรุปงานหรือเปลี่ยนทิศทาง ให้ update `CONTEXT_LOG.md` และ `NEXT_ACTION_PLAN.md` เพื่อกันบริบทหาย
