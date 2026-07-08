---
name: project-deal-checker
description: โต๊ะเช็คดีล /quote/deal (v47) — เครื่องเช็คราคา/ตั้งราคาหลายรูทของโอ deploy แล้ว 6ก.ค.
metadata: 
  node_type: memory
  type: project
  originSessionId: 9d43ed21-e60a-4dfb-9a65-d5c0b46cfccd
---

**โต๊ะเช็คดีล `/quote/deal`** — DONE + deploy 6ก.ค.2026 (commit 6aac7c6, PASS ทุก marker) ลูกค้าโยนรูท/ราคามา → วางทั้งก้อน → เห็นต้นทุน/กำไร หรือราคาที่ควรเสนอ ทุกรูทในตารางเดียว แทนการนั่งคิดทีละรูทด้วยเครื่องคิดเดิม

- **สเปค:** `docs/superpowers/specs/2026-07-06-deal-checker-design.md` (คำตอบที่โอเคาะ + สถาปัตย์ครบ)
- **ของ:** `app/deal_check.html` (หน้าเดี่ยว JS) + endpoint ใน main.py: `/quote/deal/distance|save|list|load` + ตาราง `DealRecord`+`PlaceCache` (v47 create_all)
- **resolve จุด:** คลังสถานที่ (PlaceCache จำอัตโนมัติ) → 77 จังหวัด+alias (กทม/โคราช/อยุธยา…) → ลิงก์ gmaps (ตาม short link ให้) → พิกัด → กรอก กม. เอง
- **โครงเที่ยวต่อดีล:** วงรอบผ่านจุดรับของ (แบบ Wonder) หรือวิ่งตรง (ขาเดียว/×2) — สลับแล้วต้องกดคิดระยะใหม่ (ระยะกรอกเองไม่หาย)
- **สูตร:** เอนจินต้นทุน + กติกาค่าเที่ยว (ฐาน500@250กม.+100/150กม., 10ล้อ+100, โบนัส≥3วัน) แก้ได้ต่อดีล + ตารางผันน้ำมันแบบ Wonder (% ต่อช่วงจากฐาน)
- **หลายจุดส่งต่อรูท** (โอขอ 6ก.ค. — deploy 862988f): คั่นชื่อจุดด้วย `>` เช่น "อยุธยา > สระบุรี > โคราช" → OSRM ไล่ตามลำดับ; โหมดวิ่งตรง ไป-กลับ = บวกขากลับเส้นจริง (เลิก ×2)
- **GOTCHA route ordering:** ทุก literal path ใต้ /quote ต้องลงทะเบียน**ก่อน** `/quote/{qid}` ใน main.py ไม่งั้นโดนดัก (422)
- **GOTCHA ฉีดเมนูใส่ไฟล์เครื่องมือ:** ห้าม re.search `<body>` ทั้งไฟล์ — ไฟล์ fragment มี `<body>` ใน string ของ JS (ปุ่มพิมพ์) โดนฉีดกลาง string = script ตายเงียบ ตารางว่าง (เคสจริง /quote/wonder 6ก.ค.) → `_serve_tool_page` ตัดสินจากต้นไฟล์ `<!doctype`/`<html` เท่านั้น
- **เทสต์:** สร้าง AppUser ชั่วคราว login ผ่าน TestClient (RBAC 303 ถ้าไม่ login) แล้วลบด้วย id — ท่านี้ใช้ซ้ำได้
- `/quote/wonder` ก็เข้าแอปแล้วในงานเดียวกัน — ปุ่มพิมพ์ใช้ได้จริง (พ้น sandbox) ดู [[project-wonder-sub-cost-calculator]]
- **รอโอทดลองใช้จริง** — จุดที่อาจปรับ: parser ข้อความรูปแบบแปลก, เพิ่มอำเภอในคลังพิกัด, ราคาเป้านิยาม margin ต่อราคาขาย (cost/(1−m)) ไม่ใช่ markup
