---
name: project-payroll-slip-petty-itemize
description: Slip shows petty (เงินเบิกสดย่อย) deductions line-by-line (date/รายการ/amount) instead of lump; BigC+LCB
metadata: 
  node_type: memory
  type: project
  originSessionId: 09916d86-fbc0-4c5a-bfc8-46e13949f62c
---

DONE+deployed 29มิ.ย.: สลิป (หน้า /payroll/{id}/print → ZIP per-driver ด้วย [[project-payroll-slip-zip-per-driver]]) **แจกแจงเงินหักสดย่อยรายบรรทัด** (วันที่ · รายการ · ยอด) แทนยอดรวมก้อนเดียว ตามที่โอขอ ("ไม่ยอดรวมจะได้ไม่มีคำถาม").

**ที่มาข้อมูล:** ไฟล์ `สดย่อยวังน้อย.xlsx` (โฟลเดอร์ 6.Jun ของแต่ละไซต์) — col0=วันที่ col1=ชื่อผู้เบิก col2=รายการ **col14=พขร.เบิก หัก เงินเดือน** (= ยอดหักจากคนขับต่อบรรทัด). BigC ชีท `MAY 26`, LCB ชีท `JUN 26`. (ไฟล์รวมทุกไซต์+หลายปีในแท็บเดียว, มีแถวเก่าข้ามเดือน=ผ่อนงวด งวดที่ X/10 ก็เป็นยอดหักรอบนี้).

**import:** `tools/petty_itemize.py --site BIGC|LCB` (generic) — ลบ petty ก้อนเดิม (BigC `bigc_may_petty_manual`/itemized, LCB `lcb_jun2026_petty_O`) แล้วเขียน PettyCashTxn รายบรรทัด (source `<site>_petty_itemized`, deduct_from_driver, pending) → recompute payrun. **กฎ match ปลอดภัย:** match ชื่อ→emp **เฉพาะคนที่อยู่ใน payrun รอบนี้จริง** (กันชน วิโรจน์ 2 คน[39 inactive/99 active], สมัย ราศรี[BIGC] vs สมัย อยุธยา[AYU], คนลาออก วันชัย) + exact-first-name + reject diff-surname. (BigC ทำด้วย `bigc_may_petty_itemize.py` ก่อน แล้ว generic ทีหลัง).

**ผล:** BigC net 145,356→**131,856** (คนใหม่ 3 ชรินทร์/โกสินทร์/วิทัศน์ ได้สดย่อยจริง 8,500/4,500/500 ที่ copy เดิมไม่มี). LCB net 277,457→**278,457**: ยอด petty ตรง lump เดิม 170,788 เป๊ะ; **+1,000 จาก deposit_install อภิชาติ(emp96) หาย** ตอน recompute = staleness เดิมของ draft (ไม่ใช่ petty) — **ยังไม่เช็ก/แยกเรื่อง** (LCB มิ.ย. ยัง draft).

**slip render:** หน้า `/payroll/{id}/print` route เรียก `build_payroll_slip_context` ดึง `petty_lines` (reuse single source กับหน้าสลิปเดี่ยว payroll_slip.html ที่มี logic นี้อยู่แล้ว) ใส่ใน row → template `payroll_print_all.html` วน petty_lines (วันที่|label|amount) ใต้หัว "หักสดย่อย (เบิก/เงินยืม)". `_mk_line` ตัด memo ระบบ (รวมหัก/ช่อง O) ออก.

**verified headless Chrome** ทั้ง BigC(เกรียงไกร 9 บรรทัด) + LCB(พิชิต 6 บรรทัด รวม 17,879); deploy code(main.py+template)+DB push ผ่าน Tailscale, integrity ok, login 200.

related: [[project-bigc-may-payroll]], [[project-payroll-slip-zip-per-driver]], [[feedback-merge-and-deploy-without-preview]]
