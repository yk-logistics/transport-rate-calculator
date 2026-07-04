---
name: project-lcb-deposit-jun-screenshot-reconcile
description: "LCB เงินประกัน มิ.ย. โอบอก \"เกินไป 1 งวด\" — reconcile ตาม screenshot SSO (DONE+deployed)"
metadata: 
  node_type: memory
  type: project
  originSessionId: f9e14b24-a2e2-4523-8f07-25bd5c5ed620
---

DONE+deployed 29มิ.ย.: โอแจ้งเงินประกัน LCB เดือน6 (payrun#2) "บวกเกินไป 1 งวด" + ส่ง **screenshot ชีท SSO เป็น ground truth** (`Pictures/Screenshots/Screenshot 2026-06-29 225720.png`) — คอลัมน์: ชื่อ | งวด X/10 | X | **ยอดหัก**. โอ: "หลอกตามนี้ก่อนสำหรับเดือนนี้".

**กฎที่ถูกจาก screenshot:** ยอดหัก = หักจริง.
- กลุ่มจ่ายครบ (10/10, **หัก 0**) → balance=10000=target, ไม่หัก. [10 คน]
- คนยังจ่าย (หัก 1000) → badge X = **งวดที่กำลังหัก**; balance ต้อง = **(X−1)×1000** (จ่ายแล้ว X−1 งวด); engine หัก 1000; filter `_fmt_dep_install` โชว์ paid+1 = X.
- **อภิชาติ พิเศษ: 10/10 แต่หัก 1000** (งวดสุดท้าย) → balance=9000 (ไม่ใช่ 10000).

**บั๊กเดิม:** [[project-lcb-deposit-sso-resync]] ตั้ง balance=X×1000 (X=ชีท) → สูงไป 1 งวด → (1) อภิชาติ 10/10 หัก 0 (ควรหัก 1000) (2) คนยังจ่าย badge โชว์ X+1 (พชร โชว์ 10/10 ควร 9/10). **อย่าใช้ (X−1)×1000 กับทุกคน** — กลุ่มจ่ายครบต้องคง 10000 (ถ้าลดจะหักเกิน, เคยพลาดคิดงั้นตอนแรก).

**แก้:** อภิชาติ(96) bal 10000→9000 = **money −1000** (net 276,058→275,058, net_guard allow 2 ผ่าน เฉพาะ run2 ขยับ). + 7 คนยังจ่าย (พชร84.. เอ้ย 86/พัฒิยะ84/รัฐภูมิ85/นิพล97/ณัฐวุฒิ98/วิโรจน์99/สุภาพ100) bal −1000 = **badge-only net ไม่ขยับ** (หักยัง 1000). วราวุฒิ(101) bal=0 ถูกแล้ว. ผล: badge ตรง screenshot ครบ 18 คน (MISMATCH 0). filter `_fmt_dep_install` **ไม่แก้** (paid+1 ถูกอยู่แล้ว, ปัญหาคือ balance).

**3 ชื่อใน list โอ (นิยม/วิชาญ/กฤษฎา) = ลาออก ไม่อยู่ payrun#2** → ข้าม (โอยืนยัน). deploy: --with-db scp DB fail (lock) → stop 8010 by PID(14300, เว้น 8020) → scp → byte-verify 57,524,224 → YK_MVP_APP task → 200 (ดู [[reference-deploy-mvp-selfverify]]).
