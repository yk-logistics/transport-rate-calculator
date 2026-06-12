============================================================
  YK LINE Archiver — ชุดติดตั้งเครื่อง Server
============================================================

>> ก่อนเริ่ม (ทำครั้งเดียวบนเครื่อง Server ที่ยังไม่เคยมี Python):

   A. โหลด Python 3.12 จาก https://www.python.org/downloads
      ตอนติดตั้ง **ติ๊ก "Add python.exe to PATH"** ก่อนกด Install
   B. กด Win พิมพ์ "app execution aliases"
      เปิด "Manage app execution aliases" -> ปิด python.exe และ python3.exe
      (กัน Microsoft Store มาแย่ง ทำให้ venv สร้างไม่ได้)

>> วิธีใช้บนเครื่อง Server (ทำครั้งเดียว):

   1. เสียบ flashdrive เข้าเครื่อง Server
   2. เปิดโฟลเดอร์ YK_LINE_INSTALLER
   3. ดับเบิลคลิก  INSTALL.bat
      - ถ้ายังไม่มี Python มันจะหยุดและบอกให้ทำขั้น A/B ข้างบนก่อน
      - รอจนขึ้น "Install complete!"
   4. เสร็จ! ระบบจะเปิด START.bat ให้อัตโนมัติ

>> เปิดใช้งานครั้งต่อไป (ทุกครั้งที่เปิดเครื่อง):

   ไปที่  C:\Users\<ชื่อ user>\YK_LINE_ARCHIVER
   ดับเบิลคลิก  START.bat

   จะเปิด 2 หน้าต่าง (บอท + tunnel) อย่าปิด
   URL คงที่ https://line.yklogistics.uk — ไม่ต้องตั้ง LINE ใหม่

>> อยากให้เปิดเองตอนเครื่องบูต:
   กด Win+R พิมพ์ shell:startup
   เอา shortcut ของ START.bat ไปวางในโฟลเดอร์นั้น

------------------------------------------------------------
 ⚠️ flashdrive นี้มี token/รหัสลับทั้งหมด — เก็บให้ดี
    ถ้าหายต้อง reset token LINE/Discord ใหม่
------------------------------------------------------------
