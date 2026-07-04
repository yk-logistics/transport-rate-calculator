---
name: project-b4-fleet-calendar
description: B4 ปฏิทินกำลังรถ /calendar DONE+deployed 3ก.ค. — กติกานับว่าง + GOTCHA เดลี่ไม่มี vehicle link + AYU/BIGC รอเพิ่มทะเบียนรถ
metadata: 
  node_type: memory
  type: project
  originSessionId: 742a8c2c-bba6-475f-bb99-ce05aba9b6ba
---

**B4 DONE+deployed 3 ก.ค. 2026 (commit f708de2, surgical scp 5 ไฟล์ + restart verified RESULT OK):**
หน้า /calendar เลือกไซท์ → ต่อวัน "ว่างรับงาน X คัน" = รถ active (truck/head ไม่นับหางลาก) − จอง/วิ่งจริง − ซ่อม − คนลา; คลิกวันเห็นรายคัน/คนลา + ปุ่มสร้างแผนงาน (planner prefill `?plan_date=`); ฟอร์มลงลาเร็ว (LeaveRecord ช่วงวัน กันซ้ำ ลบได้ — ตารางนี้เพิ่งถูกใช้ครั้งแรก); permissions key `calendar` office=edit (หัวหน้าไซท์ลงลา) accountant/viewer=view

**กติกาแยกแถวเดลี่ (ลอกจาก payroll _count_work_days):** status_code เป็นชื่อลูกค้า=วิ่งงาน / "รถจอด รองาน ไม่มีงาน"=ว่าง (LCB คีย์รถจอดทุกคันทุกวัน — ถ้าไม่กรอง busy=18 ตลอด) / token "ลา ขาด ป่วย" หรือ leave_status หรือ "ลาหยุด" ใน destination=ลา / "ซ่อม อุบัติเหตุ"=ซ่อมเฉพาะวัน; MaintRecord in_progress=ซ่อมตั้งแต่ work_date จนปิด

**GOTCHA:** (1) เดลี่จริงทุกไซท์ head_vehicle_id=NULL หมด — ต้อง match ทะเบียนจากข้อความ plate_no_raw (ตรงกับ Vehicle.plate_no เป๊ะ) (2) master รถมีแต่ LCB 18 คัน — **AYU/BIGC เลขว่าง=0 จนกว่าโอ/ทีมเพิ่มทะเบียน+ไซท์ที่ /vehicles** (หน้ามี banner บอกแล้ว) (3) วันลาอ่านสดจากเดลี่+LeaveRecord สองแหล่ง — ไม่ได้แก้ import ตามสเปคเดิม (โอมอบออกแบบเอง ข้อ 3 คำตอบแพลน)

verified: pytest tests/test_calendar_page.py 7 ตัว + suite เต็ม 313 pass + เทียบมือ LCB มิ.ย. 3 วัน (5/6 ว่าง0, 8/6 ว่าง1, 12/6 ว่าง1) ตรงเป๊ะ; handoff เต็มใน MVP_TASK_SPECS.md §B4

related: [[project-master-plan-jul26]] [[project-jul3-session-close]]
