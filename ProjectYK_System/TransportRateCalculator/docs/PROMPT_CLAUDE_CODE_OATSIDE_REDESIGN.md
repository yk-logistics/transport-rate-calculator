# Prompt สำหรับ Claude Code — ปรับ/ออกแบบระบบ Oatside ใหม่ทั้งหมด

คัดลอกบล็อกด้านล่างไปวางใน Claude Code (ปรับ path ถ้าเปิด workspace คนละโฟลเดอร์)

---

## คัดลอกเริ่มที่นี่

```
คุณคือโปรแกรมเมอร์ช่วยโปรเจกต์ "Project YK" — โฟกัสโมดูล **Oatside → P&G** (รายงานจากไฟล์ GPS Excel สองฝั่ง: ต้นทาง Oatside + ปลายทาง P&G)

### ผู้ใช้
- โอ = ผู้จัดการ non-coder ต้องการ **ออกแบบใหม่ทั้งระบบ Oatside ได้** แต่ต้อง **อธิบายเป็นภาษาไทย** และคงความสามารถรันได้จริง
- เป้าหมาย: สรุปให้ **ลูกค้าเห็นยอดชัด** (เที่ยวปกติ + ชาร์จ 50% + min 2 เที่ยว/วัน ถ้ายังใช้) + ตรวจทะเบียนรายคันง่าย

### อ่านบริบทก่อนลงมือ (ลำดับนี้)
1. @ProjectYK_System/TransportRateCalculator/docs/OATSIDE_TRIP_PAIRING_MERGE_HANDOFF.md
2. @ProjectYK_System/TransportRateCalculator/docs/OATSIDE_LOCAL_UPDATE_WITHOUT_UPLOAD.md
3. @Oatside/build_oatside_reports.py (ไฟล์หลัก — ถ้าเปิด workspace แคบ ให้ชี้ path เต็มจากราก repo)

### สถานะปัจจุบัน (ห้ามทำหายโดยไม่ตั้งใจ)
- จับคู่ต้น–ปลาย: greedy + **merge ต้นทางหลายช่วง** + rematch orphan + **guard ลำดับเวลา** (ถ้า Origin_In เที่ยวถัดไป < Dest_Out เที่ยวก่อน → เที่ยวก่อนไป Unmatched)
- เรทต่อเที่ยว (ตามวันที่ **Dest_In**, ปี 2026 ในโค้ดปัจจุบัน): **12–15 เม.ย. = 8,000 บาท** · **นอกนั้น = 7,500 บาท**
- ชาร์จ **50%**: เมื่อวันนั้นทะเบียนนั้นมี **matched trip = 1** ต่อวัน Dest_In (ไม่ใช้กฎ “ค่าเสียเวลา” ตาม wait threshold แล้ว)
- Override แบบจำค่า: ไฟล์ **Oatside/oatside_billing_overrides.json** (`exclude_50` / `include_50`) หรือ env **OATSIDE_OVERRIDES_JSON**
- Output: Excel `Oatside/Oatside_PG_Trip_Summary_By_Site.xlsx` + HTML ใต้ `TransportRateCalculator/reports/oatside-apr2026` + deploy script **deploy_oatside_report.ps1** (เลือกโฟลเดอร์รายงานที่ index.html ใหม่สุด)

### สิ่งที่ต้องการให้คุณทำ (ออกแบบใหม่ได้ — แต่มีขอบเขต)
1. **เสนอสถาปัตยกรรมใหม่** แยกเป็นโมดูลชัด (parse / match / billing / export excel / export html / deploy) หรือ refactor ในไฟล์เดียวก็ได้ ถ้าเหตุผลชัด
2. **UI/รายงาน**: ให้โอและลูกค้ามองเห็น **ยอดรวม** และ **รายวัน × ทะเบียน** (วันไหน 1 เที่ยว → โดน 50% หรือถูก override) โดยไม่ต้องไล่ทั้งไฟล์
3. **การตั้งค่า**: เรทช่วงวันที่, เปอร์เซ็นต์ชาร์จ 1 เที่ยว, min trips — ถ้าเป็นไปได้ให้ **อ่านจาก config (JSON/YAML)** แทน hardcode ในโค้ด (ยังมีค่า default เดิมได้)
4. **ความน่าเชื่อถือ**: log หรือชีต “ทำไมถึงคิดแบบนี้” สั้นๆ ต่อวัน/ต่อทะเบียน (audit) ถ้าคิดว่าช่วยลด dispute กับลูกค้า
5. **หลังแก้**: `python -m py_compile Oatside/build_oatside_reports.py` และรัน build กับไฟล์ตัวอย่างใน `Oatside/` ถ้ามี

### ข้อจำกัด
- Stack หลักยังเป็น **Python + openpyxl + HTML static** ได้ (ไม่บังคับ Node) — ถ้าเสนอเปลี่ยน stack ต้องบอก trade-off ชัด
- ฉลาดกับ **.cursorignore**: โฟลเดอร์ `Oatside/` อาจถูก ignore ใน Cursor — ใช้ terminal หรือ path เต็มเมื่อแก้
- ตอบโอเป็นภาษาไทย; identifier ในโค้ดเป็นภาษาอังกฤษ

### Deliverable ที่ต้องการตอนจบรอบ
- สรุปสั้นๆ: โครงใหม่เป็นอย่างไร + ไฟล์ไหนเปลี่ยน/เพิ่ม
- วิธีรันสำหรับโอ (คำสั่งเดียวหรือ bat)
- ถ้ามี breaking change กับไฟล์ overrides หรือชื่อชีต Excel ให้บอกชัด

เริ่มจากอ่านไฟล์ด้านบน แล้วเสนอแผน 1 รอบก่อนลง refactor ใหญ่ — ถ้าโอไม่ได้ขอแผนยาว ให้ลงมือ refactor ได้เลยแต่ต้องสรุปผลท้ายรอบให้ครบ
```

---

## หมายเหตุสำหรับโอ

- เปิด workspace เป็น **ราก `Project YK`** จะ `@Oatside/...` ได้ง่าย  
- ถ้าเปิดแค่ `ProjectYK_System` ให้แนบ path เต็มของ `Oatside/build_oatside_reports.py` ใน prompt แทน  
- ไฟล์ prompt นี้อยู่ที่: `ProjectYK_System/TransportRateCalculator/docs/PROMPT_CLAUDE_CODE_OATSIDE_REDESIGN.md` — พิมพ์ใน Claude Code ว่า **อ่านไฟล์นี้แล้วทำตาม** ก็ได้
