# S2 ตรวจภายในแอป — ผลตรวจ + สิ่งที่แก้แล้ว (4 ก.ค. 2569 กลางคืน)

> ตรวจโดย Fable ตามสเปค S2: audit จุดเงินครบ / เช็ค upload / path traversal /
> directory listing — สรุปให้โออ่านได้ + ให้โมเดลถัดไปตรวจซ้ำได้

## 1. Audit จุดเงิน — ครอบแล้ว (P2 + เก็บตกคืนนี้)

| จุดเงิน | ตาราง audit | สถานะ |
|---------|-------------|-------|
| แก้แถวเดลี่ (ราคา/ค่าเที่ยว/ทุกช่อง) | DailyJobAudit (เดิม) | ✅ |
| เงินประกันตน | DepositAudit (เดิม) | ✅ |
| แผนจัดรถ | DispatchPlanAudit (เดิม) | ✅ |
| ใบเสนอราคา (สถานะ/ราคาต่อรอง) | QuotationAudit (เดิม) | ✅ |
| แก้ธนาคาร/เลขบัญชีพนักงาน | AuditLog (P2) | ✅ |
| finalize รอบเงินเดือน | AuditLog (P2) | ✅ |
| ติ๊ก/ยกเลิกรับเงิน AR | AuditLog (P2) | ✅ |
| ติ๊ก/ยกเลิกรับ KB | AuditLog (P2) | ✅ |
| หนี้/วงเงิน (ยอด/งวด/ปิดบัญชี) | AuditLog (D2) | ✅ |
| แก้สิทธิ์รายชิ้นส่วน | AuditLog (P1) | ✅ |
| **ยกเลิกยอดตกหล่น (PayAdjustment)** | AuditLog | ✅ เพิ่มคืนนี้ |
| **เรทราคา (สร้าง/แก้ราคา/ลบ)** | AuditLog | ✅ เพิ่มคืนนี้ |
| import เดลี่/สดย่อย (CLI tools) | — | ⚠️ ไม่มี audit ราย field (มี preflight+จำนวนแถวใน log) — ยอมรับได้: รันโดย admin เท่านั้น |
| petty แก้มือ | มี status/lock ตาม flow | ⚠️ ยังไม่เข้า AuditLog กลาง — จุดถัดไปถ้าโอต้องการ |

ดูรวมทุกแหล่ง: **/admin/audit** (กรอง user/ตาราง/วัน/ค้นหา)

## 2. Upload ทุกช่อง

| ช่อง | ตรวจนามสกุล | ชื่อไฟล์ | หมายเหตุ |
|------|-------------|----------|----------|
| /import/sheets (Excel) | เนื้อไฟล์ต้อง parse เป็น xlsx (พังตอนอ่าน) | UUID ตั้งเอง | suffix ตามไฟล์เดิม — ไม่ถูก execute/เสิร์ฟ; แนะนำ whitelist .xlsx เพิ่มในอนาคต |
| /oatside (GPS 2 ไฟล์) | เนื้อไฟล์ต้อง parse | `Path(...).name` (กัน traversal) | admin เท่านั้น (เมนู quote) |
| /todo แนบรูป | ✅ whitelist .jpg/.jpeg/.png/.webp/.heic | ตั้งเลขเอง | ✅ |
| Driver PWA รูป | บังคับ ext=jpg ฝั่ง server | server ตั้งชื่อ (drv.save_photo) | ✅ |

ไม่มีช่องไหน execute ไฟล์อัปโหลด; ไม่มีการเสิร์ฟไฟล์ตามชื่อที่ user ตั้งตรงๆ

## 3. Path traversal / directory listing

- ทุก route เสิร์ฟไฟล์แบบ dynamic ตรวจ `resolve().startswith(base)`:
  `/oatside/report/{path}` ✅, `/line/media/{id}` ✅ (ตรวจใน service),
  `/todo/media/...` ✅ (+ ตรวจเจ้าของ), `/quote`/`/ops/...` = path คงที่ ✅
- StaticFiles (/static, /uploads) ไม่มี directory listing โดยดีไซน์ ✅

## 4. ✅ ประเด็นที่พบ — ปิดแล้ว 6 ก.ค. 2026

**`/uploads/` (รูปจากคนขับ) เคยเปิด public ไม่ต้องล็อกอิน** — ปิดแล้ว: ถอด StaticFiles
mount → route `/uploads/{path}` (main.py `serve_upload`) เสิร์ฟเมื่อมี **AppUser session
หรือ access-link token (`?t=` แบบเดียวกับ /check)** เท่านั้น + กัน path traversal
(`resolve()` + parents check); เทสต์ล็อก 7 ข้อใน `tests/test_uploads_gate.py`

ข้อกังวลเดิม "เสี่ยงพัง Driver PWA" ตรวจแล้ว**ไม่จริง**: หน้า PWA คนขับพรีวิวรูปเป็น
client-side (FileReader ก่อนอัปโหลด) ไม่เคยโหลดจาก /uploads; ผู้ใช้จริงมี 3 ทาง —
admin pages (session ✓), API ดูรูปงานใน grid (session ✓), และ `/check/mechanic`
ผ่าน magic link → แก้ template พ่วง `?t={{ token }}` ที่ URL รูปแล้ว

## 5. ของที่แข็งแรงอยู่แล้ว (จาก red-team 15 มิ.ย. — ดู SECURITY_FOR_OAT.md)

bcrypt + กันเดารหัส + คุกกี้ Secure/HttpOnly 8ชม. + HSTS/X-Frame/nosniff +
RBAC 4 บทบาท (unmapped route = admin เท่านั้น fail closed) + P1 สิทธิ์รายชิ้นส่วน
