---
name: project-slip-offtable-fuel-display
description: สลิปไม่โชว์น้ำมันนอกตาราง (วัดถังเริ่มเหมา + handover) — แก้ render ทั้ง mixed+mao (DONE+deployed)
metadata: 
  node_type: memory
  type: project
  originSessionId: f9e14b24-a2e2-4523-8f07-25bd5c5ed620
---

DONE+deployed 29มิ.ย. (main d72504a): โอแจ้ง "ไม่เห็นในสลิปคนขับเลย ทั้ง สุรเดช พชร นิพล". เงินหัก**ถูก**อยู่แล้ว (เข้า fuel_cost_self) แต่ **สลิปไม่ render** แถวน้ำมันนอกตาราง (daily_job_id=None). 2 บั๊กคนละจุด:

1. **lcb_mixed (สุรเดช/พชร):** แถววัดถัง `mao_tank_measure` อยู่ใน ctx (`tank_measure_rows`) แต่ template **branch `{% if mixed %}` ไม่มี loop tank_measure_rows** (มีแค่ branch ปกติ/else). → เติม loop (colspan=2 ตามคอลัมน์ mixed 6 ช่อง) ก่อน `</tbody>` ใน `_slip_body.html`.
2. **lcb_mao (นิพล):** แถว handover `source=handover_measure` ถูก filter `find("tank_measure")` ตัดทิ้ง → ขยายเป็น `_OFFTABLE_FUEL=("tank_measure","handover_measure")` ใน `build_payroll_slip_context`.

แสดงผลล้วน ไม่แตะเงิน. tests `test_slip_offtable_fuel_rows.py` 4 + slip suite 35 ผ่าน.

**UPDATE 30มิ.ย.: แถวคืน (amount<0) โชว์ "คืน" เขียว แทนเลขแดง.** handover ขาส่งมอบ (เช่นนิพล คืน 1,813.68) amount ติดลบ เดิมโชว์ "-1,814" แดงใน c-cut → คนขับงงว่าหักเพิ่ม. แก้ทั้ง 2 loop: `{% set _credit = t.amount < 0 %}` → ป้าย "คืนน้ำมัน"(tag-credit) + "คืน {abs}" สีเขียว(c-credit) ; amount>0 คงเดิม(หัก แดง c-cut). CSS c-credit/tag-credit เพิ่มใน **payroll_slip.html + payroll_print_all.html ทั้งคู่** (print-all CSS แยกไฟล์). deploy code-only marker `tag-credit` (อยู่ใน template → self-verify ผ่านครบ ไม่เหมือน marker ใน services/ ที่ FAIL ปลอม).

**บทเรียนตัวเอง:** เคยบอกโอผิดว่า "โชว์บนสลิป" โดยดูแค่ `tank_measure_rows` ใน **context** ไม่ได้ดู **HTML จริง** — ของจริง mixed branch ไม่ render. **ต้องเช็ค rendered HTML เสมอ ไม่ใช่แค่ context.**

**GOTCHA verify บน server:** เช็ค Thai literal ผ่าน SSH→PowerShell→python stdin = **false negative** (Thai เพี้ยนใน pipe) — render บอก "MISSING" ทั้งที่ row อยู่จริง. ใช้ **ASCII discriminator** (`html.count('class="row-tank"')` / `c-cut`) แทน → surade/pchr/nipon = 1 row-tank ครบ. + marker check ของ deploy_mvp.sh grep แค่ main.py/templates **ไม่ครอบ services/** → marker ใน services = FAIL ปลอม (โค้ด live จริง). ดู [[reference-deploy-mvp-selfverify]]. เกี่ยว: [[project-mao-fuel-tank-measure]] [[project-fuel-handover-measure-backlog]] [[project-slip-fuel-deduct-clarity]]
