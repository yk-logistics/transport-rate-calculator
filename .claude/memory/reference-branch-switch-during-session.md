---
name: reference-branch-switch-during-session
description: "Git branch can flip under you mid-session (an external process runs `git checkout`); commits land on the wrong branch — verify branch before each git mutation"
metadata: 
  node_type: memory
  type: reference
  originSessionId: e974ffa9-51c0-4619-842b-5dd26c35986e
---

ระหว่าง session ของ Claude Code บน YK repo สังเกตว่า **branch ปัจจุบันเปลี่ยนเองได้กลางคัน** — มี process ภายนอก (น่าจะ auto-resume/watcher หรือ tooling อื่น) สั่ง `git checkout` ทำให้ commit ไปลงผิด branch โดยไม่รู้ตัว.

อาการที่เจอ (2026-06-24): สั่ง `git checkout -b feat/X` แล้วทำงาน+commit แต่ commit ดันไปอยู่บน branch อื่น (`feat/lcb-daily-fuel-crosscheck`) ที่มี commit งานอื่นค้างอยู่ → พอ cherry-pick มา branch ใหม่ ได้ `main.py` ที่ปนโค้ดงานอื่น (AppSetting/slip-reader) ทำให้ ImportError.

**How to apply:**
- ก่อนทุก git mutation (commit/merge/checkout) ให้ **เช็ค branch ก่อน** ในคำสั่งเดียวกัน: `test "$(git branch --show-current)" = "<expected>" && git ...`
- หลัง commit ให้ echo `git branch --show-current` ยืนยันว่ายังอยู่ branch เดิม
- ถ้างานปนกับ commit งานอื่น: สร้าง branch จาก main ใหม่ แล้ว cherry-pick **เฉพาะ commit ของงานเรา** — แต่ระวัง cherry-pick ดึงทั้งไฟล์ (เช่น main.py) ที่มีโค้ดงานอื่นติดมา; ตรวจ `git diff --stat main..HEAD` ว่ามีแต่ไฟล์ของงานเราจริง และ grep หา symbol ของงานอื่น (เช่น AppSetting) = 0
- วิธีกู้ main.py ที่ปน: `git checkout main -- path/main.py` แล้ว re-apply เฉพาะ edit ของเราใหม่ (เขียน script replace by anchor กันพลาด) แล้ว commit

ดู [[reference-mvp-deploy-restart-gotcha]] (อีก gotcha ของ repo นี้).
