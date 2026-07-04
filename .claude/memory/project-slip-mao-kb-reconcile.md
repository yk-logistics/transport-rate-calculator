---
name: project-slip-mao-kb-reconcile
description: สลิปคนเหมา บวกค่าเที่ยวรายบรรทัดมือ ≠ ยอดรวม เพราะ KB×60% หักในยอดรวม(fuel_share_income) แต่ตารางโชว์ดิบ; +เจอ mixed KB บนวันเที่ยวไม่ถูกหัก
metadata: 
  node_type: memory
  type: project
  originSessionId: 9f837922-8b2d-4cb8-a474-823168b1cdbe
---

1ก.ค. โอถาม "ค่าเที่ยวในสลิปคนขับ บวกมือแล้วไม่เท่ายอดรวม เกี่ยว KB ไหม" → **ใช่ เกี่ยว KB (โอเดาถูก)**.

**กลไก (by design, ไม่ใช่บั๊กสำหรับ pure mao):** สลิปตารางรายเที่ยวโชว์ `trip_fee_driver` **ดิบ** ต่อบรรทัด (คนขับไม่เห็น KB=ใต้โต๊ะ). ยอดรวม = `item.fuel_share_income` = engine หัก KB แล้ว. `lcb_mao`: `fuel_share_income = Σtfd − Σ(kb×0.6)` → **ตารางΣ − ยอดรวม = KB×60%** พอดี. คนขับบวกมือเลยได้มากกว่ายอดรวม = ยอด KB×60% ที่ซ่อน. **verified run2:** ปกรณ์ ต่าง 528=KB880×0.6, พิชิต 132=220×0.6, รัฐภูมิ 198=330×0.6. คน KB=0 ต่าง=0.

**reconcile ที่ถูก (mao+mixed):** `ตารางΣ(tfd ดิบ) == fuel_share_income + trip_fee_total + Σ(kb บนแถว tfd>0)×0.6`. 10/11 คน run2 reconcile เป๊ะ.

**✅ FIXED+DEPLOYED 1ก.ค. (display-only, live):** commit branch fix/slip-trip-fee-kb-display; deploy_mvp.sh code-only --markers trip_fee_show (6/6 PASS, public 200). **live verify: ปกรณ์ Σบรรทัด=72,922.8=item.fuel_share_income server เป๊ะ** (server DB ต่างจาก Dev=ปกติ). โอสั่งให้ "บรรทัดที่โชว์บนสลิป" หัก KB ให้ตรงยอดรวม (ปกรณ์ NHL 2410 KB110 → โชว์ 1380 ไม่ใช่ 1446). ทำ helper `services/payroll_slip.py:slip_trip_fee_display(r)` = ถ้าแถว ratio≈0.60 (เหมา) → `driver_calc_price(r)×0.60`=(rev−kb)×0.6 ; แถว flat (lcb_trip 200฿ ratio~0.08) → คง tfd เดิม (KB ไม่ลดค่าเหมาจ่าย — โอยืนยัน). expose เป็น `trip_fee_show` ใน ctx; แก้ 3 surface: `_slip_body.html:146` (normal path), `payroll_print_all.html` {% with %} (+trip_fee_show=r.ctx.trip_fee_show กัน 500), `payroll_export_pdf.py:332` (FPDF bundle). **verified real DB run2: Σ บรรทัด ปกรณ์ = 70,024.2 = item.fuel_share_income เป๊ะ; 4 NHL rows โชว์ 1380, 0 rows โชว์ 1446.** ไม่แตะเงินที่จ่าย/หน้าเดลี่/stored trip_fee_driver. test `test_slip_trip_fee_kb_display.py` (4). suite 263 pass. **ไม่แตะ mixed path `_slip_body.html:70` (`revenue×0.60` inline) — โอสั่งแยกทำทีหลัง.**

**✅ FIX รอบ2 2ก.ค. (commit 4bbc304, deployed+verified):** code-review เจอ helper เดิม `(rev−kb)×0.60` **ทับค่าเที่ยวแก้มือ**: ธัชชนพล/เสรี (ayu_mao 55%: 3753→tfd 2064.15, ratio 0.55 **ชนขอบ tol ±0.05 พอดี**) โดนโชว์ 2,252 เกินจริงรวม 2,814.75/1,688.85 ใน AYU#18. แก้สูตร → **`tfd − kb×share`** (ตรง engine `Σtfd − Σkb×share` ต่อแถว; ปกรณ์ 60% เป๊ะเลขเดิม 1380; กัน price_override divergence ด้วยเพราะเลิกใช้ driver_calc_price). deploy surgical scp payroll_slip.py ไฟล์เดียว (probe server==HEAD~1 ก่อนทับ), restart by 8010-PID, verify: venv python รัน helper บน server 4 เคส PASS + public 200 + 8020 รอด. **GOTCHA server: start_mvp.bat ใช้ .venv แล้ว (memory เก่าบอก global python = ล้าสมัย); global python ไม่มี sqlmodel.** เคสค้างเล็ก: lcb_mao แถว flat+KB (92 สองแถว 9/5, 93 หนึ่งแถว 7/5) engine หัก 66/แถว แต่สลิปโชว์ดิบ — ratio-gate ไม่รู้ pay_mode, รอทำพร้อม mixed.

**✅ RESOLVED โอตัดสิน 2ก.ค. + FIX รอบ3 (fd82714, deployed+verified):** โอเคาะกฎ = **KB ผูกกับ 'คน' ไม่ใช่แถว**: คนเหมาหักทุกแถว / คนรายเที่ยว KB ไม่แตะค่าเที่ยวเลย (วันเที่ยวของ mixed ก็ไม่หัก → engine ที่ไม่หักวันเที่ยว **ถูกอยู่แล้ว ไม่ใช่งานเงิน**) / **คนลูกผสมช่วงเหมาต้องหัก**. ทำ: helper รับ `pay_mode` dispatch (lcb_mao→tfd−kb×share ทุกแถว; lcb_mixed วันเหมา→(price−kb)×0.6 ตาม engine, วันเที่ยว→ดิบ; โหมดอื่น→ดิบ); bind pay_mode ใน build_payroll_slip_context (`trip_fee_show` lambda) → สลิป/print/ZIP/PDF ตรงกันเอง; ตาราง mixed เลิก inline rev×0.60 → `trip_fee_show(r)`. ปิดเคส: mixed วันเหมา+KB (86 สองแถว 6/6, 91 สามแถว 9-10/6 โชว์ 1,380), lcb_mao แถว flat+KB (92/93 โชว์หลังหัก), เทสต์เก่า print_all คาด 3,300 ดิบ → อัปเดตเป็น 3,100 หลังหัก. **commit เทคนิค: _slip_body.html มีงาน k-tag อีก session ค้าง → commit จากไฟล์ HEAD+hunk ผมเท่านั้น แล้วคืน worktree; deploy 3 ไฟล์จาก commit (ไม่ใช่ worktree).**

**✅ CFO/P&L หัก KB แล้ว (2ก.ค. b9aa8bd, deployed+verified):** โอสั่ง "เห็นทุกขั้นตอน ไม่ซ่อน" → monthly_pnl เพิ่ม `kb_return`=Σkb_amount เป็นบรรทัดแยก, `revenue_total`=ขนส่ง+ค่าอื่น−KB, กำไร/margin คิดจากรายรับจริง; โชว์ /finance breakdown + /finance/pnl คอลัมน์ "−KB คืน" + SUM_FIELDS/totals 2 route; live LCB มิ.ย. kb 4,400. **ตัด KB เต็ม 100% ไว้ก่อน** — สูตรคืนจริง (โอน 90%/ใบ ณ ที่จ่าย 3%) ค่อย refine พร้อม [[project-cy-kb-payout-calculator]].

**✅ ZIP สลิปไม่อัปเดต (2ก.ค. commit เดียวกัน):** ตัว ZIP สร้างสดจาก DB ทุกครั้ง (uuid work dir) — ปัญหาจริง=ชื่อไฟล์ซ้ำเดิม (ทั้งชื่อไทย+ascii fallback payroll_slips.zip) → โหลดหลายรอบ Windows เติม (1)(2) ให้ไฟล์ใหม่ โอเปิดไฟล์ชื่อเดิม=อันเก่าสุด; แก้=ประทับ `สร้างdd-mm-yy_HH.MM` ในชื่อ zip ทั้งสองแบบ + no-store.

related: [[project-lcb-mao-pertrip-pay]] (mao หัก KB ต่อเที่ยว), [[project-kb-driver-calc-price]] (driver_calc_price=price−kb), [[project-lcb-mixed-mode]]
