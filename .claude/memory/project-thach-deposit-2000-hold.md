---
name: project-thach-deposit-2000-hold
description: "ธัชชนพล เงินประกันตน งวดละ 2,000 + พักหักรอบ มิ.ย.; engine+filter รองรับงวดละต่อคน — DONE+deployed"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5958b1e8-62e6-4533-af2d-1c3e111a9801
---

DONE+deployed 30มิ.ย. (main 688f54d): ธัชชนพล(emp143 AYU) เงินประกันตน **งวดละ 2,000** (ไม่ใช่ 1,000 มาตรฐาน), สะสมแล้ว 11 งวด=**22,000**, เป้า **30,000** (15 งวด); โอสั่ง**พักหักรอบ มิ.ย.นี้** (ตัดออกก่อน).

**โค้ด (รองรับต่อคน, ไม่กระทบคนอื่น):** Employee.custom_terms JSON 2 คีย์ใหม่
- `deposit_install_unit` (เช่น 2000) → engine payroll หักงวดละค่านั้น (เดิม min(1000,remaining) ตายตัว); filter `_fmt_dep_install`+ใหม่ `_dep_install_unit` โชว์ X/Y ด้วยหน่วยนั้น (11/15 ไม่ใช่ 22/30 ที่หาร 1,000)
- `deposit_hold: true` → engine ข้ามหักรอบ (deposit_install=0) แม้ bal<tgt; filter โชว์งวด=**paid (จ่ายแล้ว) ไม่ +1** เพราะรอบนี้ไม่หัก (โอยืนยันอยาก 11/15 ไม่ใช่ 12/15)

DEPOSIT_INSTALL_UNIT(=1000) ยัง default คนทั่วไป. ตั้ง ธัชชนพล bal=22000 tgt=30000 ct={"deposit_install_unit":2000,"deposit_hold":true} (data fix) → recompute 4 mao: deposit_install 1000→0, net −41,078.24→**−40,078.24**, run18 194,067.46→**195,067.46**; net_guard --allow 18 OK; 58 tests pass; live display=11/15, public 200. **สลิป/payroll ซ่อนบรรทัดเงินประกันเมื่อ deposit_install=0 อยู่แล้ว** (templates `{% if item.deposit_install %}`) → ไม่โชว์งวดบนสลิปรอบนี้; เลข X/Y โชว์เฉพาะหน้า /deposits.

**UPDATE 30มิ.ย.: สลิปไม่โชว์ประกันเลยตอน hold+ยังไม่ครบ** (bal22k<tgt30k, deposit_install=0) — ตกร่องระหว่าง if(ผ่อน)/elif(ครบ bal>=tgt). เพิ่ม branch 3 ใน `_slip_body.html`: มี target แต่ไม่หักรอบ+ยังไม่ครบ → "เงินประกัน (สะสม 22,000) งวด 11/15 — เดือนนี้ไม่หัก" (main 7861017, code-only). regen 31 สลิป.

deploy: code (payroll.py+main.py) + DB WAL-safe ([[project-ayu-mao-pertrip-pay]] _ayu_mao_deploy.ps1; probe server ก่อน). related: [[project-deposit-installment-number]], [[project-office-no-deposit]], [[project-thach-fuel-jun]]
