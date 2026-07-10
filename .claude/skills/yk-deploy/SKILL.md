---
name: yk-deploy
description: ขั้นตอน deploy Project YK ขึ้น server production (app.yklogistics.uk) พร้อม self-verify — ใช้ทุกครั้งที่จะเอาโค้ด/template/docs ขึ้น server, restart แอป, scp ไฟล์ไปเครื่อง YK, หรือโอบอก "ขึ้นเลย / deploy / เอาขึ้น server / อัปเดตหน้าเว็บ"
---

# Deploy Project YK → server

## ทางหลัก (โค้ดแอป)

```bash
bash ProjectYK_System/tools/deploy_mvp.sh --markers "<ascii-marker-in-new-code>"
```

- marker ต้องเป็น **ASCII เท่านั้น** (ห้ามไทย) และต้องมีอยู่จริงในโค้ดที่เพิ่งแก้
- สคริปต์ copy **ทั้ง dir** — ถ้า working tree มีไฟล์ค้างจาก session อื่น ให้ **scp เฉพาะไฟล์ที่แก้** (surgical) แทน
- ห้าม `git add -A` เด็ดขาด — stage เฉพาะ path ที่ตั้งใจ (เคยลาก DB backup 1.7GB เข้า commit)

## Gotcha ที่เคยเจ็บจริง

- **restart แอป: kill โดย PID ที่ถือพอร์ต 8010 เท่านั้น** — ห้าม filter ชื่อ process ".venv" (เคยฆ่า LINE archiver พอร์ต 8020 ไปด้วย)
- **oatside config บน server เป็นตัวจริง ห้ามทับ** — ก่อน copy dir เช็คว่าไม่มี config ทับ
- ssh: `yklog@100.97.150.114` (Tailscale) passwordless — quote ซ้อนบน ssh พังง่าย → เขียน `.ps1` แล้ว scp ไปรันแทน
- `.ps1` ที่ scp ไปรัน **ห้ามมีภาษาไทย** (SYSTEM account ไม่มี UTF-8 console)
- แอปบน server รันเป็น **SYSTEM** — อะไรที่เรียก `claude` CLI ฝั่ง server ต้องเทสต์ในสิทธิ์ SYSTEM ไม่ใช่ user yklog
- Scheduled task ใหม่บนเครื่องโอ (โน้ตบุ๊ก): ตั้ง `AllowStartIfOnBatteries` + `StartWhenAvailable` + `ExecutionTimeLimit=PT0S` เสมอ
- แก้ schema → อัปเดต `SCHEMA_VERSION` ใน main.py + ALTER block ใน lifespan() พร้อมกันทุกครั้ง

## เกณฑ์เขียว (ครบทุกข้อถึงพูดว่า "deploy แล้ว" ได้)

- [ ] marker โผล่ในไฟล์บน server (deploy_mvp.sh เช็คให้ หรือ ssh grep เอง)
- [ ] `curl -s -o /dev/null -w "%{http_code}" https://app.yklogistics.uk/health` = 200
- [ ] เปิด**หน้าที่แก้จริง** 1 หน้า เห็นของใหม่ (curl เนื้อหา หรือ screenshot ถ้าเป็น display)
- [ ] ถ้าแก้ schema: server รายงาน SCHEMA_VERSION ตัวใหม่
- [ ] ถ้าแตะเงิน/DB: ผ่านสกิล yk-money-task มาก่อนแล้ว

รายละเอียดเต็ม: `ProjectYK_System/docs/MVP_SERVER_DEPLOY.md`
