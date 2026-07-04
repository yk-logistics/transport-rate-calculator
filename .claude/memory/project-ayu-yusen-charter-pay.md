---
name: project-ayu-yusen-charter-pay
description: "AYU-Yusen charter driver-pay calculator (60% mao) — spec done, paused, waiting for โอ to resume"
metadata: 
  node_type: memory
  type: project
  originSessionId: 34dbe0e9-eeea-47c7-a1bb-a88f2b515677
---

PAUSED 29มิ.ย. (spec เขียน+commit แล้ว ยังไม่เขียนโค้ด) — โอจะกลับมาทำต่อเอง: เครื่องคิด **ค่าขนส่งคนขับเหมา AYU ลูกค้า Yusen (Charter)** = 60% ของรายได้สุทธิจริงต่อเที่ยว

**Spec:** `docs/superpowers/specs/2026-06-29-ayu-yusen-charter-driver-pay-design.md` (commit 877561f บน branch feat/slip-zip-chrome-pdf)
**ไฟล์ต้นทาง:** `CHARTER Y.K. <เดือน>.xlsx` (โอส่งไฟล์ พ.ค. มาศึกษา = ใบวางบิลที่ YK เก็บจาก Yusen)

**สูตร (โอยืนยันแล้ว):** ต่อเที่ยว `driver_pay = TotalCost × effective_rate × 0.60`; effective_rate = NET รวมรอบ ÷ ΣTotalCost; NET = ΣCost×(1+surcharge)+extras −1% −TMS (อ่าน TMS/labor/discount auto จาก block ท้ายไฟล์ด้วยคำในป้ายไทย, ไม่ลอกเลขแถวตาย)
- **surcharge คิดสดจากราคาน้ำมันของรอบ** (ตาราง range ในไฟล์: 28-29.99=0%, +2%/2฿ ขึ้นไป; นอกตาราง extrapolate `floor((p−28)/2)×2%`)
- **GOTCHA สำคัญ:** ไฟล์ พ.ค. ที่โอส่ง คิด 12% (ราคา 40.99 = รอบ 26/4-25/5) — **ไม่ใช่บั๊ก**; เดือนถัดไป 26/5-25/6 ราคา 39.88 → ต้อง 10% ฉะนั้นห้ามลอก effective_rate ดิบจากไฟล์ ต้องคิด surcharge ใหม่จากราคา
- ราคาน้ำมัน = "ราคาน้ำมันอ้างอิงของรอบ" (avg ไฮดีเซล S บางจาก ตามช่วงรอบลูกค้า) — **โอกรอกเอง** (มีเครื่องมือ yk-logistics.github.io/transport-rate-calculator แคปหน้าจอบางจาก); ไม่ scrape เว็บ

**ไม่ทำ:** ไม่แตะ payrun/DB/FuelTxn/payroll.py (กัน session อื่น); **ไม่หักค่าน้ำมันคนขับเติม** (โอคิดต่างหาก — งานนี้คิดเฉพาะค่าขนส่ง 60%); ไม่ deploy จนโอตรวจ
**ตรวจย้อน:** Σdriver_pay = NET×0.60 เป๊ะ (พ.ค. ใส่ราคา 40.99 ต้องได้ NET 55,302.75 → ×0.6 = 33,181.65)
**คนขับ Yusen 4 คน:** เรวัตร, รุ่งเรือง, วัชร์นล นันทะเดช, สมปอง = กลุ่ม ayu_mao ที่ค้าง "เหมารอราคา" ใน [[project-ayu-jun-payroll]] (ราคานี้แหละที่จะเติมให้)
แผนถัดไปเมื่อ resume: writing-plans → TDD (งานเงิน). related: [[project-ayu-daily-import]], [[project-dhl-overflow-rate]] (สูตร surcharge ผูกราคาน้ำมันคล้ายกัน)
