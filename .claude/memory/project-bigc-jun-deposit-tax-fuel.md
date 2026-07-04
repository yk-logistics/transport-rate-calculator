---
name: project-bigc-jun-deposit-tax-fuel
description: "BigC#4 (พ.ค. รอบจ่าย 1ก.ค.) 1ก.ค.: เงินประกันตนอัปตามรูปโอ DONE; ภาษีถูกต้องตามวิธีเดียวกับ LCB (โอตัดสิน); น้ำมัน/สลิป BigC ค้าง"
metadata: 
  node_type: memory
  type: project
  originSessionId: a7be03e9-a1b6-49f9-babb-fcf28b790466
---

**1ก.ค. (โอส่งงานชุดท้าย ใกล้เช้า "ขอให้จบ Perfect"):**

**B6 เงินประกันตน BigC#4 — DONE+deployed (server net 126,859→132,859, +6,000):**
โอส่งรูป (Screenshot 050759) งวดประกันตนรอบปัจจุบัน. ใช้กฎ LCB-proven [[project-lcb-deposit-sso-resync]]: **badge X = งวดกำลังหักรอบนี้; ยังจ่าย(X<10) balance=(X-1)×1000 หัก 1000; ครบ(10/10) balance=10000=target หัก 0.** target=10000 (10งวด). ค่าจากรูป: เกรียงไกร/สมประสงค์/ธนวัฒน์/สมัย/เกศศักดิ์/ณัชพน = **10/10 หยุดหัก net+1000** (6คน +6,000); เสกสรร/มานพ=3/10, โกสินทร์/วิทัศน์/ชรินทร์=2/10 (ยังหัก 1000). **9000 ในรูป = ฐาน SS ไม่เกี่ยว deposit** (โอย้ำ). **ไม่ full-recompute** (BigC#4 มี override recompute=ผิดมหาศาล) — set deposit_balance/target บน Employee (badge) + แก้ item.deposit_install/net/deduction_total ตรงเฉพาะ 6 คนที่เปลี่ยน. tool scratchpad bigc_deposit_srv.py (portable, รันบน server ตรงๆ กัน clobber LCB#2). net_guard: เฉพาะ run4 ขยับ.

**B7 ภาษี BigC — ถูกต้องตามวิธีเดียวกับ LCB (ไม่ใช่บั๊ก, รอโอตัดสิน policy):**
`_compute_income_tax_withholding` (payroll.py:502) **shared ทุกไซต์ ไม่ branch** — ใช้ `_real_income = gross − fuel_cost_self` (YTD-avg projection). **ณัชพน(108,bigc_monthly) ภาษี 168** เพราะ fuel_self=0 (BigC บริษัทออกน้ำมัน ไม่หักคนขับ) → taxable = gross เต็ม 28,203 × 12 เกิน threshold. ต่างจาก LCB mao ที่ fuel_self สูง→post-fuel income ต่ำ→ภาษี 0. **= วิธีคิดเหมือนกันเป๊ะ ณัชพนแค่รายได้สุทธิหลังน้ำมันสูงกว่า. ถ้าโอไม่อยากเก็บภาษี BigC → ใส่ tax_exempt (custom_terms) หรือ policy ไซต์** (โอตัดสิน). ณัชพน YTD 6 เดือน gross 26-34k/เดือน.

**A5+B8 สลิป BigC — DONE+deployed (commit feat/bigc-slip-polish, marker _bigc):** site-conditional `_bigc = run.site_code=='BIGC'` ใน `_slip_body.html`: ข้ามแถวเติมน้ำมันล้วน(tag-fuel น้ำตาล), ไม่โชว้ลูกศร↳วันซ้ำ(เว้นว่าง), ไม่โชว้ doc_no/remark เทาต่อท้ายส่งสินค้า; **เพิ่มกล่อง "น้ำมันที่ได้" = `item.fuel_rate_income/16` (ลิตรที่ทำได้, ติดลบ=หักคนขับ แดง)** ในการใช้รถ/น้ำมัน (grid 4 col). ตรงไฟล์เรท (เกรียงไกร 139.8L=2236.62/16, สมประสงค์ −16.6L). LCB/AYU ไม่กระทบ.

**คืนเงินประกันตน 3 คนลาออก → LCB#2 DONE+deployed (server 276,871→286,871, +10,000):** นิยม82(7000)/วิชาญ83(2000)/กฤษฎา102(1000) (โอตรวจแล้ว amount; bal ระบบ 8000/3000/2000 ต่างจากที่โอบอก 1000 → ใช้ตามโอ). add PayRunItem standalone gross=net=refund หัก0 note "คืนเงินประกันตน X (ออกแล้ว...)" tnote "ออก-คืนประกัน" + zero deposit_balance. ลอกแบบ เรืองฤทธิ์ AYU#18. รันบน server ตรงๆ กัน clobber LCB#2 (local stale 271,074). วันชัยกลับมารอบ7 ไม่คืน (หักครบ ใช้ต่อ). tool scratchpad deposit_refund.py.

**(เดิม) B8 ไฟล์อ้างอิงน้ำมัน BigC:**
- โออยาก: ตรวจน้ำมัน BigC จากไฟล์ `2564Daily Report (04.21).xlsx` ชีท `เดือน06.21` คอลัมน์ **M-S** (ไมล์/ลิตร/ราคาต่อลิตร/บาท/เรท/ลิตรที่คนขับทำได้/หมายเหตุ) + ไฟล์ `เรทน้ำมันเดือนพฤษภาคม69.xlsx` แยกรายคน (**L=เรท กม./ลิตร, M=ลิตรที่ได้ ติดลบ=หักคนขับ ทำเรทไม่ได้**).
- สลิป BigC ประยุกต์ LCB: **เอาออก** ป้ายน้ำตาล "เติมน้ำมัน"(row-fuelonly/tag-fuel)/ลูกศร↳/อักษรเทาต่อจากส่งสินค้า(ถ้าไม่ใช่เลขเอกสาร→ดึงจากหมายเหตุ); **เพิ่ม** คอลัมน์ "น้ำมันที่ได้(ลิตร)" ในรายการวิ่งงาน. = ต้อง site-conditional ใน _slip_body (BigC vs LCB) + อาจ import ลิตรที่ได้.

**A1-A3 หน้าสรุปบอส DONE+deployed:** totband "รวมรายได้"→"รายได้หลังหักน้ำมัน(%)"; ปกต +badge งวด x/10; KB +(%ขนส่ง). A4: slip ใช้ AYU/BigC ได้ไม่เพี้ยน (driver_fees=0 ไซต์อื่น=ไม่โชว้ tag ปกติ).

related: [[project-lcb-deposit-sso-resync]], [[project-bigc-may-payroll]], [[project-lcb-bigc-jun-payroll-review]], [[project-slip-fuel-fill-date]], [[project-lcb-jun-payroll-audit-fixes]] (tax YTD method)
