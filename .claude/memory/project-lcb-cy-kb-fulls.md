---
name: project-lcb-cy-kb-fulls
description: "LCB CY-customer KB fill — 23 CY rows kb=0 need KB (full, before 10% owner-cut); exact per-invoice KB amount NOT in shared sheets, โอ says it's in Google Drive"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9f837922-8b2d-4cb8-a474-823168b1cdbe
---

**⚠️ แก้รอบสอง 3ก.ค. 01:14 (backup app-pre-revert840):** โอเคาะกติกาสุดท้าย — **คนขับคิดจาก "ราคาที่คีย์" เสมอ ส่วนต่างชื่อไฟล์เข้าบริษัท** → ถอน +840: 7 แถว kb_amount = 5000−ราคาคีย์ (914/916/917/922: 8→308, 806/998/993: 616→716) + หัก item 6 คนตรงๆ (ห้าม recompute! รอบ finalized สดย่อย=deducted แล้ว engine sum กรอง pending → recompute จะทำสดย่อยหาย) run2 กลับ 286,871.37; เงินเจ้าของงานไม่กระทบ (/kb-payout อ่านไฟล์ตรง ไม่ใช้ kb_amount). **กติกาถาวร: คีย์เดลี่ลูกค้า KB = ราคาที่ต้องได้จริง; KB ฝั่งคนขับ = 5000−คีย์; KB ฝั่งเจ้าของงาน = จากไฟล์อินวอย (คนละตัวได้ ส่วนต่างเข้าบริษัท)**

**✅ DONE รอบแรก 3ก.ค. 00:47 (บน server, backup app-pre-cykb-20260703-0047.db):** โอเคาะทาง B + ยึดชื่อไฟล์ → ลง 23 แถว (rev→5000, mao tfd→3000, kb ตามไฟล์), recompute 9 คนเฉพาะจุด, run2 net 286,871.37→287,711.37 (+840 = จ่ายคืน ณัฐวุฒิ/ปกรณ์/พิชิต/พชร +180, วราวุฒิ/วิโรจน์ +60), รอบอื่น Δ0, ทุกเช็ค PASS. **GOTCHA: ชีทเดลี่ Google ยังเป็นราคาเก่า — re-import LCB จะทับ fix นี้! ต้อง sync ชีท (ถามโอ) หรือกัน re-import ช่วงนี้.** เดิม: preflight — `docs/PREFLIGHT_CY_KB_2026-07-02.md`** (จับคู่ 23 แถว↔ไฟล์อินวอย Drive ครบ, KB รวม 11,184; **ค้นพบ: ราคาเดลี่ CY = ราคาเสนอหัก KB แล้ว → เงินคนขับปัจจุบันถูกอยู่แล้ว ((5000−KB)×60% เป๊ะ) → เสนอทาง B: แก้ rev→5000 + ใส่ kb พร้อมกัน เงินคนขับไม่ขยับ; ทาง A (ใส่ kb เฉยๆ) = หักซ้ำ −2,956.80**; 7 แถวราคาชนกัน (2606-002 เสนอ 4992 vs เดลี่ 4692 ต่าง 300/ตู้!) รอโอชี้; ห้ามแตะ DB จนกว่าจะเคาะ)

BLOCKED-on-input 1ก.ค. — โอสั่ง "ใส่ KB งานลูกค้า CY ราคาเต็ม ไม่หัก 10%".

**ความหมาย "ราคาเต็ม ไม่หัก 10%"** (โอยืนยัน): เก็บ `DailyJob.kb_amount` = **KB เต็ม** ไม่ต้องลบ 10% ที่บริษัทหักให้เจ้าของงาน. 10%/WHT คิดสดอยู่แล้วใน `services/kb.py` (`KB_OUR_CUT=0.10`, `KB_WHT=0.03`) ไม่เก็บ field. = ตรงกับดีไซน์เดิม [[project-kb-driver-calc-price]] (kb_amount = KB เต็ม, split คิด report-time).

**ข้อมูล CY รอบนี้ (cycle 2026-06, tab `Daily 16.05.69 - 15.06.69`):** 23 แถว status_code=CY, **ทุกแถว kb_amount=0** (ลืมกรอก). แต่ละแถวมีเลขอินวอยใน **col AB (ออกอินวอย)** = `CYIV2605-xxx`/`CYIV2606-xxx`. KbRule CY = default_kb 0 + required=1 (เตือนกันลืม).
- Y ค่าขนส่ง (idx24) = 4,200/4,284/4,692/4,600; Z รวมเก็บ (idx25) = Y + X(ค่ายก/ผ่านลาน/คลีน...); **ไม่มีคอลัมน์ KB ในชีต**.
- คนขับ CY 15 คน: **9 เป็น mao/mixed** (รัฐภูมิ/พชร/สุภาพ/นิพล/วราวุฒิ/ณัฐวุฒิ/ปกรณ์/พิชิต/วิโรจน์) → KB ลดเงินเขาจริง `(price−KB)×60%`; 6 เป็น lcb_trip → KB display-only.

**ที่ค้าง (ต้องได้จากโอ):** ตัวเลข KB ต่ออินวอย CY ไม่ได้อยู่ใน 3 sheet ที่ service account เห็น (`Daily แหลมฉบัง2`, `Daily โฮมโปร-ทั่วไป`, `สดย่อย LCB`) และไม่อยู่ใน repo docs/memory. โอบอก "เคยคุยใน session อื่น อยู่ Google Drive" — **แต่ Drive file นั้นยังไม่ได้แชร์ให้ service account** (`guolekung@` หรือ share ไฟล์ KB ให้ `noble-history-446303-e4-...@...gserviceaccount.com`). ต้องได้ไฟล์/ตัวเลข KB ต่ออินวอยก่อนถึงจะ backfill+recompute ได้. **อย่าเดายอด KB = งานเงิน.**

**GOTCHA display:** เจอบั๊กป้ายหัวคอลัมน์ daily_grid (แก้แล้ว รอ deploy) — trip_type_code(G) ติดป้าย "รับตู้(H)" เลื่อน 1 ช่อง; DB ถูกต้อง แก้เฉพาะ label+preset ใน templates/daily_grid.html.

related: [[project-kb-driver-calc-price]], [[project-lcb-mao-pertrip-pay]], [[reference-google-sheets-access]]
