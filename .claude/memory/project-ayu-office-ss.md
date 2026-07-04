---
name: project-ayu-office-ss
description: AYU office 9 คน ตั้งประกันสังคม (450/750 ตามฐาน 9000/15000) — DONE+deployed; ซองอู/พร/จอมิน/เก้า รอ onboard เป็น office
metadata: 
  node_type: memory
  type: project
  originSessionId: 5958b1e8-62e6-4533-af2d-1c3e111a9801
---

DONE+deployed 30มิ.ย. (DB-only) payrun#18: ตั้ง SS office AYU 9 คน (เดิม SS=0), net ลดตาม SS:
- 450 (ฐาน 9,000): พงษกาญจน์115, จุฑามาศ116, พิชญา(ข้าวฟ่าง)120, บรรเจิด(เอ๊ะ)121, พบ122, **ศราวุธ124 (เอา ss_exempt ออก!** เดิมตั้งไว้ตอนทำ [[project-ayu-office-changnoi-sarawut]] แต่จริงๆส่ง SS)
- 750 (ฐาน 15,000): สมภพ117, Nan khan hon san 118, หัสยา(ตาล)119

set social_security_base+rate บน employee + **set SS บน PayRunItem ตรงๆ + net−=SS** (office ลอกยอด ไม่ recompute). รวม SS 6×450+3×750=**4,950**; run18 236,117.59→**231,167.59**; net_guard รอบอื่นนิ่ง; live public 200, พงษกาญจน์ SS 450 net 20,550.

**ค้าง — office AYU ที่ขาด (โอถามว่าขาดใคร):** **ซองอู126/พร127/จอมิน128/เก้า129** มีในระบบแต่เป็น `ayu_trip/role=driver` base=0 ไม่มี daily **ไม่อยู่ใน run18**; โอบอกเป็น **คนงาน/แม่บ้าน (office)** → ต้องแปลงเป็น office_monthly + ใส่เงินเดือน + SS + เข้า run18 — **รอโอให้เงินเดือน/SS**. "คนงาน" (ชื่อตรงๆ) ไม่มีในระบบ. **+แม่บ้านคนใหม่** (เริ่ม 12/6 เงินเดือน 12,000 รอบ 1-31 เฉลี่ย 12000/30 เดือนแรกไม่เต็ม) ยังรอทำ. related: [[project-ayu-jun-payroll]], [[project-ayu-office-changnoi-sarawut]]
