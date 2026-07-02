# Runbook: Oatside ในระบบ MVP (/oatside)

> คู่มือส่งต่อ — คน/โมเดลเล็กทำตามได้ ไม่ต้องรู้บริบทอื่น

## โอใช้ยังไง (ไม่ต้องมี AI เลย)
1. โหลดไฟล์ "รายงานการผ่านจุด" จากเว็บ GPS 2 ไฟล์ (ฝั่ง Oatside + ฝั่ง P&G) เป็น .xlsx
2. เข้า **เมนู เงิน → 🚚 Oatside** → เลือก 2 ไฟล์ → กด "คำนวณใหม่" (รอ ~1 นาที)
3. ดูผล: ปุ่ม "ดูรายงาน" (หน้าเดียวกับ github.io เดิม) / "Excel สรุป" ไว้วางบิล
4. แก้เงื่อนไข: ปุ่ม "⚙️ แก้เงื่อนไขเอง" — เรทตามช่วงวัน, ราคาดีเซลรายวัน, วันลูกค้าหยุด,
   ตัดเที่ยวตีเปล่า, เที่ยวขากลับ/manual, ยกเว้น +50% — **บันทึกแล้วต้องกด "คำนวณใหม่" เลขถึงเปลี่ยน**
   ทุกการบันทึกมีสำรองไฟล์เดิมอัตโนมัติ (.bak-เวลา เก็บ 20 ชุด อยู่ใน app/oatside/)

## โครงระบบ (สำหรับคนแก้โค้ด)
- engine = `app/oatside/build_oatside_reports.py` **สำเนา byte-identical จาก `Oatside/` ราก repo — ห้ามแก้ที่สำเนา** แก้ต้นทางแล้ว copy+deploy (ดู app/oatside/README.md)
- ระบบเรียก engine เป็น subprocess (`services/oatside_runner.py`) ผ่าน env OATSIDE_ORIGIN/OATSIDE_DEST — ไม่ import เข้าแอป
- output: `app/oatside/Oatside_PG_Trip_Summary_By_Site.xlsx` + HTML ที่ `app/oatside/TransportRateCalculator/reports/oatside-apr2026/` (route /oatside/report เสิร์ฟตัวนี้ก่อน)
- เงื่อนไข: `app/oatside/oatside_config.json` + `oatside_billing_overrides.json` — หน้า /oatside/settings เขียนกลับพร้อม backup; แก้บน server มีผลทันทีที่รันครั้งถัดไป (ไฟล์บน server เป็นตัวจริง — ถ้าแก้ผ่านหน้าเว็บแล้ว **อย่า scp config จาก dev ไปทับ**)
- เทสต์: `tests/test_oatside_center.py` · เกณฑ์ตรวจ: ไฟล์ GPS 4/6/2026 ต้องได้ **152 เที่ยว / unmatched 22 / checksum ชีทราคา 1,485,120.00**

## กู้คืน
- เงื่อนไขพัง: เอา .bak ล่าสุดใน app/oatside/ มา rename ทับ แล้วคำนวณใหม่
- รายงานเพี้ยน: ดู log ในหน้า /oatside (รอบล่าสุด) — engine พิมพ์สาเหตุ; ไฟล์ GPS ผิดฟอร์แมต = พังตั้งแต่ parse
