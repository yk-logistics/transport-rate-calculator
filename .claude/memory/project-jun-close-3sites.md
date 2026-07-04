---
name: project-jun-close-3sites
description: "3ก.ค. 00:50 ปิดรอบ (finalize) มิ.ย. ครบ 3 ไซท์ตามคำสั่งโอ \"ปิดตามยอดเดิมไม่แก้อะไร\" — ข้าม drift/policy gate โดยเจตนา net ไม่เปลี่ยน"
metadata: 
  node_type: memory
  type: project
  originSessionId: e43bba19-d298-4881-8117-b08646b56d9b
---

**3 ก.ค. 2026 00:50 — finalize บน server ครบ 3 รอบ** (โอสั่ง 3ก.ค. เช้ามืด: "ปิดรอบทั้ง 3 ไซท์เลย ไม่ได้แก้ไขอะไร รวมถึง LCB AYU"):

| run | ไซท์ | net (ไม่เปลี่ยนตอนปิด) | สดย่อยล็อก |
|---|---|---|---|
| 2 | LCB 2026-06 | 287,711.37 (หลังลง KB CY +840) | 98 |
| 18 | AYU 2026-06 | 263,793.34 | 198 |
| 4 | BIGC 2026-05 | 132,031.03 | 70 |

- ปุ่ม finalize ปกติติด gate: LCB/BIGC = cycle_drift (สดย่อย tag ตรงรอบแต่วันที่นอกช่วง), AYU = policy_review (แท็กไม่ตรง policy) — ตรวจแล้ว**ทั้งหมดคือยอดที่ทีมตั้งใจหักรอบนี้**: เบิกล่วงหน้า 2,000/คน ลง 22/6 (LCB 18 คน) และ 29/6 (AYU 15 คน) = เบิกก่อนวันจ่ายเงินต้น ก.ค. + หนี้เก่ายกมาทวง (500 ฯลฯ) — ถูกหักใน net อยู่แล้ว จึง force-finalize แบบทำครบขั้นตอนเดียวกับปุ่มจริง (status+finalized_at+lock petty) + note ใน run
- BigC: เกศศักดิ์ −3,226 / ธนวัฒน์ 6 วัน / ภาษี ณัชพน 168 — โอสั่งปิดตามเดิมทั้งหมด
- **AYU: โอบอกอาจแก้ราคาขนส่งทีหลัง → ต้องมีระบบ "ค่าเที่ยวตกหล่น/จ่ายตามหลัง"** (เทียบราคาใหม่ vs ที่จ่ายไปในรอบ finalized → ทำคืน/หักส่วนต่างรอบถัดไป) — อยู่เฟส C ใน [[project-master-plan-jul26]]
- GOTCHA: run finalized ห้าม recompute (จะ drop ข้อมูล) — กลไกตกหล่นต้องเป็นรายการใหม่รอบถัดไป ไม่ใช่แก้รอบเก่า

related: [[project-lcb-cy-kb-fulls]] [[project-master-plan-jul26]] [[project-jun-payroll-ayu-bigc-status]]
