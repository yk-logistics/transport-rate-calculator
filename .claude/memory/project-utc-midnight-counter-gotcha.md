---
name: utc-midnight-counter-gotcha
description: "บั๊ก timezone ตัวนับ \"คัดแล้ววันนี้\" — DB เก็บ utcnow แต่เทียบเที่ยงคืนไทย พังช่วง 00:00-07:00; แก้ด้วย _local_midnight_utc() 13ก.ค."
metadata: 
  node_type: memory
  type: project
  originSessionId: 5cd89889-5b67-400c-afe0-6690bf99c63e
---

ระบบเก็บ timestamp ทุกตาราง (updated_at / LineJobSeen.at ฯลฯ) ด้วย `datetime.utcnow()`
แต่โค้ดที่นับ "ตั้งแต่เที่ยงคืนวันนี้" เคยใช้ `datetime.combine(date.today(), min.time())`
= เที่ยงคืน**เวลาไทย** → ช่วง 00:00–07:00 ไทย ตัวนับเป็น 0 ทั้งที่เพิ่งทำงานไป
(เทสต์ test_inbox_page_shows_today_progress / test_inbox_shows_done_today_counter
fail เฉพาะรันก่อน 7 โมงเช้า — กลางวันผ่านปกติ)

**แก้แล้ว 13 ก.ค. 2026:** helper `_local_midnight_utc()` ใน main.py (ใกล้ `_month_bounds`)
แปลงเที่ยงคืนไทย→UTC ก่อนเทียบ — ใช้ที่กล่องบิล (done_today) และ line inbox แล้ว

**Why:** เทสต์/ฟีเจอร์ใหม่ที่เทียบ "วันนี้" กับคอลัมน์ที่ default เป็น utcnow ต้องผ่าน helper นี้
**How to apply:** จะนับ/กรองอะไร "ตั้งแต่เที่ยงคืน" กับ timestamp UTC → เรียก `_local_midnight_utc()`
อย่าสร้าง midnight เอง; ถ้าเจอเทสต์ fail เฉพาะตอนกลางคืน ให้สงสัยคลาส timezone นี้ก่อน
