# ส่งไม้ 23 ก.ค. 2026 — เตรียมปิดรอบ ก.ค. เสร็จระดับ draft, พักรอสัญญาณ

> โอสั่งพักเซสชัน: "เวลาเรียกทำงาน MVP ค่อยมาต่อ" — เซสชันหน้าเริ่มจากไฟล์นี้ + memory index
> อ่านคู่: `reports/LCB_AYU_2026-07_CLOSE_PREP_2026-07-23.md` (รายละเอียดตัวเลข+ลิสต์คน) ·
> CHANGELOG หัวข้อ 2026-07-23 · HANDOFF_2026-07-12 (กติกาทั่วไปยังใช้)
> สถานะระบบ: server ปกติ (login 200) · **pytest เต็ม 750 passed (23ก.ค.)** · git main push ครบ · tree สะอาด

## สถานะใหญ่: รอบเงินเดือน ก.ค.

**run 19 = LCB 2026-07 draft** (18 คน net 507,667.20 — หักน้ำมัน+สดย่อยแล้ว) ·
**run 20 = AYU 2026-07 draft** (31 คน net 203,011.10 — ยังไม่มีสดย่อย/office/น้ำมันวัดถัง)
ทั้งคู่ reconcile สองทางไฟล์↔engine ตรงทุกคน (LCB 18/18, AYU 13/13) · net_guard นิ่ง · preflight MEDIUM

## งานค้าง — รอสัญญาณอะไร / ได้แล้วทำตามไหน

| งาน | รอสัญญาณ | เมื่อได้สัญญาณ ทำตาม |
|---|---|---|
| **ปิด LCB run 19 (เลยกำหนด 15/7 แล้ว — เร่งสุด)** | ทีมคีย์ค่าเที่ยว 4 วันอาทิตย์ (21/6, 28/6, 5/7, 12/7) ในชีทเดลี่แหลม — เช็คด้วย `tools/check_lcb_daily_keyed.py` | export ชีทสด→แท็บ Daily (ท่าอยู่ใน PAYROLL_CYCLE_CLOSE_RUNBOOK §7 แถว import_lcb_daily) → **เช็คก่อน wipe: ห้ามมีใครแก้ grid LCB/ประทับเลขใบระหว่างนี้** → re-import `--wipe-prior` → `lcb_link_drivers.py` → recompute → `lcb_reconcile_run.py` → runbook §5-6 (deposit/KB/สลิปสุ่ม) → finalize |
| **โอเคาะคนขับ LCB** | โอตอบ: วันชัย (emp 81 inactive — ล้าง end_date?) + onboard สมหมาย ภูมิสาขา / อนันทร์ แก้วคำ / ภูมิชัย แสนศรีมน (pay_mode/บัญชี/งวดประกันตน) | แก้ Employee → รัน `lcb_link_drivers.py` + `import_lcb_petty_cycle.py --cycle 2026-07 --payrun-id 19` ซ้ำ (idempotent ทั้งคู่) → recompute |
| **ปิด AYU run 20 (กำหนด 25/7)** | ถึงวันปิด + สดย่อยวังน้อยเข้าถึงได้ (โอแชร์ gsheet ให้ `yk-sheets-editor@noble-history-446303-e4.iam.gserviceaccount.com` หรือทีมวางไฟล์ 7.Jul) + รูปเงินเดือน office จากโอ | re-import สุดท้าย (`_run_ayu_import.ps1` + `--wipe-prior` — เช็คก่อน wipe เหมือนเดิม) → link → petty วังน้อย → copy office จากรูป (ท่า มิ.ย.: memory ayu-office-reconcile-rup) → น้ำมันเหมาวัดถัง → reconcile (สคริปต์ `reconcile_run20.py` อยู่ home server) → finalize |
| **โอเคาะคนขับ AYU** | โอตอบ: ไกรวิชญ์ ชัยสีดา (38 แถว/14,100) · บุญนาม มหาพล (รถร่วม — รอสูตร 13% ด้วย) · ชัยเจริญ บุญขัน · อดิศักดิ์ กล้าหาญ (21/5,000) · อุดมชัย (1 แถว) · ปรีชาหายจากชีทหลัง 3/7 ลาออก? | เหมือนแถว LCB: แก้ Employee → link → recompute |
| BIGC ปิดต้น ส.ค. (วิ่ง มิ.ย. tag 2026-06) | ไฟล์ทีม `7.Jul/BigC/` (ยังไม่มีโฟลเดอร์) | `import_bigc_daily.py` cycle 2026-06 เตรียมแล้ว + runbook เดิม; อย่าลืมเช็คยอดสมัยถูกหัก 10,000 (memory petty-pending-audit) |
| สดย่อยค้างท่อรอบปิดแล้ว 14 รายการ/14,399.16 (preflight ธง HIGH ทุกครั้ง — ของเก่า ไม่ใช่ของใหม่) | โอ/ทีมเปิด PDF LCB พ.ค. เทียบรายคน | `reports/PETTY_PENDING_AUDIT_2026-07-12.md` — หักแล้ว→settled_offline รายแถวด้วย id; ไม่ได้หัก→C4 |
| ทะเบียนใบวางบิล ↔ ไฟล์ทีมใน Drive (KTIV/NHIV/… อัปเดตรายวัน SA มองเห็นอยู่แล้ว) | โอตัดสินให้ทะเบียน in-app เป็นตัวจริง / สั่ง sync | ออกแบบ importer จากไฟล์ Drive เข้า v52 (ยังไม่เขียน — งานใหม่) |
| /todo inbox ค้าง 15 รายการ (13ก.ค. — เบิกยาง/แจ้งซ่อม/ลาป่วย) | โอบอกทีมเริ่มใช้ /todo ทุกเช้า | ไม่มีงานเทคนิค — เป็นเรื่อง adoption |
| F3 ดันต่อ (strong 31% เพดานเพราะ NHL/DHL BPD/KTL/Wonder เลขงานอยู่ในตัวรูป) | โอเคาะทำ OCR (มีต้นทุน) | ดีไซน์ใหม่ ยึด measure_pod2.py เป็นเกณฑ์วัด; เลขวัดล่าสุดใน PLAN_STATUS F3 |
| งานเดิมจาก HANDOFF 12ก.ค. ที่ยังรอเหมือนเดิม | — | กล่องบิล 306 ใบรอโอคัด · X6 เบิกรายสัปดาห์ LCB รอโอเคาะ 5 ข้อ · สปส. วิธีบันทึกการโอนคืน รอโอเคาะ · A5 สลิปรอโอดูของจริง · D1 ~420 เส้นทางรอราคาจากโอ |

## ของที่วางไว้บน server (ใช้ต่อได้เลย)

- `YK_MVP/tools/`: lcb_import_2026-07.xlsx (ไฟล์ import ปัจจุบัน) · petty_lcb_2026-07.xlsx · ayu_gsheet.xlsx (สด 23ก.ค.) + เครื่องมือครบ (import_lcb_daily, lcb_link_drivers, import_lcb_petty_cycle, lcb_reconcile_run, net_guard, fuel_slip_reconcile, preflight_payrun)
- home (`C:\Users\yklog\`): `create_jul_payruns.py` (recompute draft 19/20 + พิมพ์รายคน) · `reconcile_run20.py` (reconcile AYU)
- gotcha ห้ามลืม: **โหมดเหมาเก็บ Σค่าเที่ยวใน `fuel_share_income`** · **import เดลี่แล้วต้องผูก FuelTxn ด้วย ไม่งั้น net โป่ง** (lcb_link_drivers ทำให้) · net_guard `--allow 19,20` ใช้ comma
