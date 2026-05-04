# AccidentCases Decision Log

## 2026-04-21

### Template + Report baseline
- ย้าย `Doc No.` ออกจากกรอบหัวกระดาษ และวางใต้ header
- เปลี่ยน Timeline เป็น 3 คอลัมน์: วันที่, เวลา, เหตุการณ์
- ปรับระยะย่อหน้าในข้อ 1/2 ให้เท่าข้ออื่น
- ปรับ wording หลักฐานเป็น `ภาพหลักฐานแนบ`
- ปรับลายเซ็นเป็น 2 ช่อง: ผู้จัดทำรายงาน, ผู้ขับขี่รับทราบ
- เพิ่มตัวช่วยรันรวมที่ `AccidentCases/run_local_server.bat`

### Evidence + printing stability
- รองรับโหลดรายการหลักฐานจาก `assets/images` เมื่อจำเป็น
- กันไฟล์ระบบ `yk_logo_mark.svg` ไม่ให้เข้า evidence
- ปุ่มพิมพ์รอรูปโหลด (`eager + decode`) ก่อน `window.print()`
- อัปเดต template ให้รองรับ evidence preview และพิมพ์ติดรูป

### Usage policy
- แนะนำเปิดผ่าน `http://localhost:8765` เพื่อให้ behavior เสถียร
- เปิด `file://index.html` ได้เฉพาะงานแก้ข้อความพื้นฐาน
