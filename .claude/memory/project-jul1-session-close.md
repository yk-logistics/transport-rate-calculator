---
name: project-jul1-session-close
description: 1 ก.ค. session close — LCB+BigC เงินเดือน มิ.ย. ตรวจ+ปรับสลิปยกใหญ่+เงินประกันตน/คืนประกัน DONE บน server; ค้าง=ภาษี BigC (โอตัดสิน) + สลิป session อื่นแก้ต่อค้าง uncommitted
metadata: 
  node_type: memory
  type: project
  originSessionId: a7be03e9-a1b6-49f9-babb-fcf28b790466
---

**1 ก.ค. (ทำยาวข้ามคืน ถึงเช้า, โอปิด session):** ตรวจทาน+ทำเงินเดือน LCB+BigC มิ.ย. + ปรับสลิปตาม feedback โอ ~15 รอบ. ทั้งหมด **draft ยังไม่ finalize** (โอ finalize เอง).

**สถานะ server (live app.yklogistics.uk, public 200) ตอนปิด:**
- **LCB#2 (มิ.ย. 16/5–15/6) net 286,871.37** = base 276,871 (session อื่น per-trip+KB) + คืนประกันตน 10,000 (นิยม/วิชาญ/กฤษฎา).
- **BigC#4 (พ.ค. จ่าย 1/7) net 132,031.03** = deposit installment (+6,000 จาก 126,859) แล้ว **session อื่น recompute ลด −828** (commit `e10e4bf`/`874261d` per-trip−KB×60% ค้าง uncommitted) — เลขนี้ที่ session อื่นกำลังทำต่อ ไม่ใช่ของผม.
- ชื่อคนขับ**ลบ นาย/นาง ออกหมด**ทุกไซต์ (names_prefixed 0).

**งานเงินที่ผมทำ+deploy บน server (DB-only, รันบน server ตรงๆ กัน clobber, net_guard เฉพาะรอบที่ตั้งใจ):**
1. **ลบคำนำหน้าชื่อ** 100 ชื่อ ([[project-lcb-bigc-jun-payroll-review]]).
2. **BigC เงินประกันตน** ตามรูปโอ (6 คนครบ 10/10 หยุดหัก, ที่เหลือ 2-3/10) ([[project-bigc-jun-deposit-tax-fuel]]).
3. **คืนเงินประกันตน 3 คนลาออก → LCB#2**: นิยม82(7,000)/วิชาญ83(2,000)/กฤษฎา102(1,000) แบบ เรืองฤทธิ์ (PayRunItem gross=net=refund, tnote "ออก-คืนประกัน", zero bal). วันชัยกลับรอบ7 ไม่คืน.

**สลิป (display, deploy หลายรอบ) — ดู [[project-slip-fuel-fill-date]] ครบ:** น้ำมันโชว้วันเติมจริง(txn_date)+B7/B20/พิเศษ/OT เรียงคอลัมน์เล็ก+ค่าเที่ยวใหญ่กว่า, เที่ยวแทนวัน, ซ่อนบรรทัดน้ำมันคนรายเที่ยว, ฐาน ปกส back-calc(=หักจริง/rate ไม่ใช่ config ตายตัว), เงินประกันตน, เงินเบิกซ่อนหมวดซ้ำ+เต็ม, หน้าบอส %ในวงเล็บ+ปกส/ปกต/หักอื่น+งวด, **สะอาดทุกไซต์** (เอาป้ายน้ำตาล/↳/เลขเอกสารเทาออก ; LCB เก็บแถวน้ำมันไว้เพราะหักจริง ; route_remark คงไว้).
- **บทเรียน "ZIP/สลิปยังเก่า":** ZIP + /slip ใช้ payroll_slip.html + build_payroll_slip_context เดียวกัน = ถ้าสลิปถูก ZIP ถูก. "ยังเก่า" = **เบราว์เซอร์ cache** (แก้: `Cache-Control: no-store` บน /slip+/print commit `a491b3f`) หรือ styling site-specific ที่ยังไม่ครบ — **ไม่ใช่โค้ด stale** (พิสูจน์ด้วย render_slip_html บน server เทียบ marker tag-fuel/tripv). **โอต้อง hard-refresh (Ctrl+Shift+R) 1 ครั้งบนแท็บเก่า.**

**⚠️ ค้าง / ต้องรู้เมื่อกลับมา:**
- **ภาษี BigC — รอโอตัดสิน (ไม่ใช่บั๊ก):** ณัชพน108 ภาษี 168 เพราะ BigC บริษัทออกน้ำมัน(fuel_self=0)→รายได้คิดภาษีสูง ; วิธีคิดเหมือน LCB ทุกไซต์. ถ้าโอไม่อยากเก็บ → ใส่ tax_exempt.
- **session อื่นแก้สลิปต่อ (uncommitted!):** branch `fix/slip-trip-fee-kb-display`, working tree มี `_slip_body.html`/`payroll_slip.html`/`payroll_print_all.html` แก้ค้าง (CSS `.c-extra`/`.k-tag` = พิเศษ/OT แยกคอลัมน์แทนซ้อน + ป้าย k-tag เหมา/เที่ยว/รถจอด นำหน้า route แทนคอลัมน์ "ฝั่ง"). **อย่าทับ/revert** — เป็นงานที่กำลังทำต่อ. commit ล่าสุด 874261d/e10e4bf.
- **local app.db STALE** (LCB#2 271,074 < server 276,871 = ปกรณ์/ณัฐวุฒิ) — **ห้าม push local DB ทับ server**. งานเงินทำบน server ตรงๆ.

related: [[project-slip-fuel-fill-date]], [[project-bigc-jun-deposit-tax-fuel]], [[project-lcb-bigc-jun-payroll-review]], [[reference-deploy-mvp-selfverify]], [[reference-branch-switch-during-session]]
