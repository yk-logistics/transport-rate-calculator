---
name: project-thach-fuel-jun
description: "ธัชชนพล AYU เพิ่ม 2 บิลน้ำมัน รอบ มิ.ย. (ยกยอด +3,960 / ทำคืน −3,164.06) — DONE+deployed"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5958b1e8-62e6-4533-af2d-1c3e111a9801
---

DONE+deployed 30มิ.ย.: โอเพิ่มน้ำมันธัชชนพล(emp143, ayu_mao 55%) ใน gsheet AYU แล้วให้ดึงมาลงระบบ. ดึงจากชีต **id `1F5eJlYsNAGi1zzm1Ej-dlk7Jcp6EEUz8cq1Om4n5VnQ` tab `Jun 26`** (รอบ 26/5–25/6; fuel cols M=ลิตร N=ราคา/ล O=บาท P=สถานี). พบ 2 ยอดที่ยังไม่อยู่ใน DB (อีก 7 บิลตรงอยู่แล้ว):
- **r13 26/5/2026 "ยกยอด"** = 112.5 L, **+3,960.00** (หักเพิ่ม)
- **r817 25/6/2026 "ทำคืน"** = −84.38 L, **−3,164.06** (ยอดติดลบ=คืนน้ำมันคนขับตอนตัดรอบ ลดยอดหัก)

insert FuelTxn 2 บิล source=`ayu_2026-06_manual` exclude_from_driver=0 ผูก daily_job_id วันเดียวกัน (id 2040/2041); fuel sum 33,164→**33,959.94** (9 บิล, สุทธิ +795.94). recompute เฉพาะ 4 mao ([[project-ayu-mao-pertrip-pay]] tool ayu_mao_recompute_run18.py) → เฉพาะธัชชนพล net −40,282.30→**−41,078.24** (Δ−795.94), อีก 3 นิ่ง. net_guard --allow 18 OK รอบอื่นทุกไซต์นิ่ง. run18 194,863.40→**194,067.46**.

**ยืนยัน rate ธัชชนพล/เสรี = เหมา 55%** (tfd=rev×0.55 ทุกแถวในเดลี่) — ระบบจัดการถูกแล้วหลัง [[project-ayu-mao-pertrip-pay]] (อ่าน trip_fee_driver ไม่ fix 60%). ธัชชนพลยังติดลบเพราะ น้ำมัน33,960+petty36,630 > ค่าขนส่ง 30,962 (คีย์เดลี่แค่ 16 เที่ยว) — รอโอตรวจ petty/รายได้ ไม่ใช่บั๊ก rate.

deploy: DB-only WAL-safe (probe server ก่อน=194,863.40 ตรง ไม่ทับงาน เรวัตร handover ของ session อื่น → backup-API+wal_checkpoint(TRUNCATE)→app_incoming.db→_ayu_mao_deploy.ps1 stop8010/integrity/swap/start). live: integrity ok, 9 บิล 33,959.94, net −41,078.24, public 200. related: [[project-rewat-handover-fuel-jun]], [[reference-google-sheets-access]], [[reference-net-guard]]
