# Forward Insight Demo - Menu Coverage Checklist

อัปเดตล่าสุด: 2026-05-07

## วิธีใช้
- `[done]` = เปิดหน้าแล้วและเห็นหน้าหลัก/ตารางใช้งานจริง
- `[partial]` = เปิดได้บางส่วน แต่ยังไม่ได้ไล่ action ในหน้านั้น
- `[todo]` = ยังไม่ได้เปิดหน้านั้น

## 1) ขนส่ง (Transport)

- [done] รายการโครงการ (`/tms/project`)
- [done] เที่ยววิ่งงาน (`/tms/trip`)
- [done] เอกสารวิ่งงาน (`/tms/shipment`)
- [done] รายงานยอดวิ่งงาน (`/tms/report/amount_trip`)
- [done] สินค้าจัดส่ง (`/tms/product`)
- [done] ประเภทสินค้าจัดส่ง (`/tms/product-type`)
- [done] สถานที่จัดส่ง (`/tms/place`)
- [done] ทะเบียน/รถวิ่งงาน (`/tms/vehicle`)
- [done] ประเภทรถวิ่งงาน (`/tms/run-type`)
- [done] วิธีจ่ายเงินผู้รับเหมา (`/tms/pay-type`)
- [done] ค่าใช้จ่ายพิเศษ (`/tms/extra`)

## 2) การจัดซื้อ (Procurement)

- [done] ตั้งเบิกค่าใช้จ่าย (`/managing-withdrawals/expense`)
- [done] รายการค่าใช้จ่าย (`/managing-withdrawals/expense-item`)
- [done] เบิกของจากสต๊อก (`/managing-withdrawals/stock`)
- [done] รายการเติมน้ำมัน (`/tms/refuel`)
- [done] ฟลีทการ์ด (`/tms/fuel-card`)
- [done] ปั๊มน้ำมัน (`/tms/fuel-station`)

## 3) บัญชี (Accounting)

- [done] เมนูย่อยแสดงครบใน mega-menu และเปิดหน้าจริงครบแล้ว
- [done] เอกสารการวิ่งงาน (`/account/tms-document`)
- [done] ใบวางบิล (ขารับ) (`/account/bill_income`)
- [done] ใบแจ้งหนี้ (`/account/invoice_income`)
- [done] ใบสำคัญรับ (`/account/payment_income`)
- [done] ใบวางบิล (ขาจ่าย) (`/account/bill_pay`)
- [done] ใบตั้งหนี้ (`/account/invoice_pay`)
- [done] ใบสำคัญจ่าย (`/account/payment_pay`)
- [done] รายการเที่ยววิ่ง (`/account/carrier/invoice`)
- [done] รายการค่าใช้จ่าย (`/account/carrier/expense`)
- [done] สรุปรายการค่าขนส่ง (`/account/carrier/bill`)
- [done] แบ่งชำระ (`/account/carrier/finance`)
- [done] ปรับปรุงรายการบัญชี (`/account/adjusting_entries`)
- [done] ภาษีถูกหัก/หัก ณ ที่จ่าย (`/account/monthly_wht`)
- [done] ภาษีประจำเดือน (`/account/vat/monthly_vat`)
- [done] ขาย (`/account/vat/tax_sale`)
- [done] ซื้อ (`/account/vat/tax_purchase`)
- [done] ภาษี (`/account/tax`)
- [done] สมุดบัญชี (`/account/journal`)
- [done] ผังบัญชี (`/account/new_account`)
- [done] GL (`/account/report/gl`)
- [done] งบทดลอง (`/account/report/trial-balance`)
- [done] งบกำไร-ขาดทุน (`/account/report/pnl`)

## 4) บุคคล (HR)

- [done] รายการการจ่ายเงินเดือน (`/hr/payroll`)
- [done] รายละเอียดรอบจ่ายเงินเดือน (`/hr/payroll/{id}`)
- [done] รายการเงินสะสม (`/hr/saving`)
- [done] ประเภทรายได้ (`/hr/income-type`)
- [done] แพ็คเกจรายได้ (`/hr/income-package`)
- [done] รายการประกันสังคมประจำเดือน (`/hr/sso`)
- [done] เอกสารรถ (`/vehiclemanage/taxandInsurance`)
- [done] รายการครบกำหนด (`/dashboard/document`)
- [done] พนักงาน (`/hr/employee`)
- [done] หน่วยงาน (`/tms/site`)
- [done] ตำแหน่งงาน (`/hr/department`)
- [done] คำนำหน้า (`/hr/title`)

## 5) ตั้งค่า (Settings)

- [done] เมนูย่อยแสดงครบใน mega-menu และเปิดหน้าจริงครบแล้ว
- [done] คู่ค้า (`/partner`)
- [done] กำหนดการแจ้งหนี้ (`/settinginvoice`)
- [done] รูปแบบการนำเข้าไฟล์ Excel (`/excel`)
- [done] สินค้า (`/core/product`)
- [done] หมวดหมู่สินค้า (`/core/product-category`)
- [done] หน่วยวัด (`/uom`)
- [done] รถ (`/core/vehicle`)
- [done] รุ่นรถ (`/core/vehicle-model`)
- [done] ประเภทรถ (`/core/vehicle-type`)
- [done] ยี่ห้อรถ (`/core/vehicle-brand`)
- [done] เชื้อเพลิง (`/core/vehicle-energy`)

## หมายเหตุรอบสำรวจ
- ระบบมี loading overlay ค่อนข้างถี่ ควรเว้นจังหวะและรอให้ overlay หายก่อนคลิกถัดไป
- หลายหน้าใช้ pattern เดียวกัน: filter panel + data table + action ต่อแถว
