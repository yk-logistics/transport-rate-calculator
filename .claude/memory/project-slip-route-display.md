---
name: project-slip-route-display
description: Slip ส่งสินค้า column shows full route ต้นทาง→โหลด→ปลายทาง; BigC skips polluted origin
metadata: 
  node_type: memory
  type: project
  originSessionId: 09916d86-fbc0-4c5a-bfc8-46e13949f62c
---

DONE+deployed 29มิ.ย.: ช่อง "ส่งสินค้า" ในสลิปโชว์ **ต้นทาง → โหลด → ปลายทาง** เต็ม (เคยแก้แล้วแต่ revert เพราะ deploy ทับกันหลาย session — โอบ่น "กลับมาเป็นอย่างเดิม").

**helper:** `delivery_route_text(r)` ใน `services/payroll_slip.py` — **สูตร route แยกต่อไซท์** (โอ 29มิ.ย.: "เดลี่คนละแบบในแต่ละไซท์ สูตรก็ต้องไม่เหมือนกัน แก้เป็นไซท์ๆ ไป"):
- **LCB** = origin → pickup_location → destination (3 ช่วง)
- **AYU** = pickup_location → destination (= ขึ้นสินค้า col5 → ส่งสินค้า col7; ลูกค้า col4 แยก; โอยืนยัน)
- **BIGC** = destination อย่างเดียว (คอลัมน์ E=สถานะ ลง origin ผิด, ไม่มี pickup)
- อื่นๆ = fallback origin→pickup→dest

template เรียกผ่าน `route_text`. AYU เดลี่ไฟล์ `Work\Salary\2026\6.Jun\AYU\Daily โฮมโปร-ทั่วไป.xlsx` ชีท `Jun 26` (col0 วันที่/1 ทะเบียน/2 ประเภทรถ/3 พขร/4 ลูกค้า/5 ขึ้นสินค้า/6 รหัสสาขา/7 ส่งสินค้า/8 เลขที่/9 ค่าขนส่ง/10 ค่าเที่ยว/12 ลิตร/13 ราคา/14 บาท). **AYU ยัง 0 DailyJob ในระบบ → route AYU โชว์ได้เมื่อ import เดลี่ AYU ก่อน (งานถัดไป, 46 emp + payrun copied-net 5 รอบ)**.

**ที่แก้ (ให้ทุกสลิปใช้ helper เดียวกัน):**
- `payroll_slip.html` (หน้ากดรายคน /payroll/{run}/employee/{emp}/slip): branch **ปกติ(else)** เดิมโชว์ `r.destination` อย่างเดียว → เปลี่ยนเป็น `route_text(r)`. (branch mixed-mode มี route_text อยู่แล้ว). หัวคอลัมน์ → "ส่งสินค้า (ต้นทาง → โหลด → ปลายทาง)".
- `payroll_print_all.html` (หน้าพิมพ์รวม + ZIP แยกคน): `d.dest` → `d.route`, หัวคอลัมน์ใหม่.
- `main.py _slip_daily_rows`: เพิ่ม field `"route": delivery_route_text(d)`.

**สำคัญ — BigC ข้าม origin:** `delivery_route_text` เช็ก `site_code=='BIGC'` แล้ว**ข้าม origin** เพราะ import แรก map **คอลัมน์ E (สถานะงาน 2BigC/Oatside/2BH)** ลง `origin` ผิด ([[project-bigc-column-e-customers]]) + BigC `status_code` ว่าง + `pickup_location` ว่าง. ถ้าไม่ข้ามจะได้ garbage "Oatside → ส่งP&G..." → BigC โชว์ destination อย่างเดียวจนกว่าจะแก้ import ให้เก็บ E แยก. LCB origin/pickup/dest เป็น leg จริง (KERRY→คาโอDC อมตะ→UNIWISE) โชว์เต็ม.

verified headless Chrome ทั้ง LCB(เต็ม) + BigC(สะอาด ไม่มี status prefix); deploy code-only + **verify ไฟล์บน server จริงว่าไม่ revert** (svc/printall/slip OK). GOTCHA: deploy ทับกันได้ → หลัง deploy ต้อง grep ไฟล์ server ยืนยัน.

related: [[project-payroll-slip-zip-per-driver]], [[project-payroll-slip-petty-itemize]], [[project-bigc-column-e-customers]], [[reference-deploy-via-tailscale]]
