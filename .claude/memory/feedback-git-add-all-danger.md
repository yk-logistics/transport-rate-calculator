---
name: feedback-git-add-all-danger
description: "NEVER git add -A in this repo — drags 30+ app.db.bak_* (57MB each, ~1.7GB) + tmp_uploads into commits; stage explicit paths only"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 91ddce0a-48bd-4312-affe-febfb58477d1
---

`git add -A` / `git add .` ในrepo Project YK = อันตราย.

**Why:** working tree มีไฟล์ค้างเยอะที่ไม่ควร commit — `app.db.bak_*` 30+ ไฟล์ (57MB/ตัว ~1.7GB รวม), `tmp_uploads/*.xlsx`, reports ที่ generate, jan_lcb_full.txt. `.gitignore` มี `*.bak`/`*.db.backup*` แต่ backup ชื่อ `app.db.bak_<tag>` (ลงท้าย _tag ไม่ใช่ .bak) เลย **ไม่ match** หลุดเข้า git ได้. (มี backup เก่าบางตัวถูก commit ไว้ในประวัติแล้วจากก่อนหน้า — pre-existing, อย่าไป rewrite history.)

**How to apply:** stage เฉพาะไฟล์ที่ตั้งใจเสมอ — `git add docs/x ProjectYK_System/tools/y.py`. night-run 2026-06-27 เพิ่ม `.gitignore`: `app.db`, `*.db.bak_*`, `app.db-wal/-shm`. ถ้าเผลอ add-all แล้ว: `git reset --soft HEAD~1` + unstage db/bak + commit ใหม่เฉพาะของจริง.
