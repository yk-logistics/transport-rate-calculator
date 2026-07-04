---
name: reference-deploy-mvp-selfverify
description: "Deploy the MVP with deploy_mvp.sh (self-verifying) — it proves new code is live, archiver up, public 200; replaces eyeballing deploy_mvp_to_server.sh"
metadata: 
  node_type: memory
  type: reference
  originSessionId: d74d681f-065b-452c-9ee6-7d1bcd291f0b
---

**Default deploy command is now `deploy_mvp.sh`, not `deploy_mvp_to_server.sh`.** It does the
copy + cutover AND verifies the deploy on the server, so a green run is real instead of eyeballed.
This was built 29มิ.ย. to fold the repeated deploy GOTCHAs into one self-checking script
(the "Loop Engineering" idea: turn a hand-checked step into a measurable goal).

```bash
bash ProjectYK_System/tools/deploy_mvp.sh --markers "<ascii-unique-to-this-change>"
bash ProjectYK_System/tools/deploy_mvp.sh --with-db --markers "..."   # also push app.db
```

Mechanism: bash copies code (+ optional app.db) + scp's `_deploy_remote.ps1` to the server,
then runs that .ps1 BY PATH (inline SSH quoting mangles `$` — confirmed again while building this).
The .ps1 prints PASS/FAIL per check and `exit 1` on any FAIL → fails the bash → non-zero exit.

Checks (each closes a GOTCHA from [[reference-mvp-deploy-restart-gotcha]] / [[reference-deploy-via-tailscale]]):
1. **app.db byte-size == Dev** before restart (only `--with-db`) — refuses to restart onto a partial scp.
2. free 8010 by **PID + `YK_MVP` cmdline** (NOT bare `\.venv` → that kills the 8020 LINE archiver).
3. new 8010 owner **StartTime ≥ main.py mtime − 5s** — catches "old global-python code still serving".
   (Verified StartTime is readable for the SYSTEM-task process — no Access-Denied.)
4. **port 8020 still up** — archiver survived the cutover.
5. **ASCII `--markers` present** in main.py/templates on server — guards revert/stale (Thai over SSH = false negatives).
6. public **app.yklogistics.uk/login → 200**.

ALWAYS pass `--markers` with a string unique to the change shipped — that arg is what proves the
new code went live (vs just "files copied"). Old `deploy_mvp_to_server.sh` left in place but its
restart is unreliable; prefer this. Runbook updated: `docs/MVP_SERVER_DEPLOY.md`.
See [[reference-mvp-server-deploy]].

**⚠️ CRITICAL 30มิ.ย. — `--with-db` byte-size check is NOT enough: app.db เป็น WAL mode → raw scp = DB พังบน server.**
local `app.db` ใช้ `journal_mode=wal` → main file **ไม่ใช่ DB ครบ** (page ล่าสุดอยู่ใน `app.db-wal`). scp แค่ `app.db` ดิบ (โดยเฉพาะตอน app เปิดอยู่/checkpoint กลางคัน) ได้ snapshot ไม่ consistent → server `PRAGMA integrity_check` = "2nd reference to page / never used" = **corrupt** ทั้งที่ **byte-size ตรง** (57,524,224==57,524,224 ก็ยังพัง). อาการ: app รัน 200 ได้แต่ query เด้ง `database disk image is malformed`.
**วิธีถูก (ทำสำเร็จ): copy ด้วย SQLite backup API ก่อน scp** — `src.execute('PRAGMA wal_checkpoint(TRUNCATE)'); dst=sqlite3.connect('clean.db'); src.backup(dst)` ได้ไฟล์เดียว consistent ไม่พึ่ง -wal → scp ไฟล์ clean นั้น → server integrity_check=ok. ลำดับกู้: stop 8010 → scp clean→`app_incoming.db` → **verify integrity ขณะ stop** → ลบ `app.db-wal`/`app.db-shm` เก่า → Move-Item ทับ app.db → start. **ห้าม scp app.db ดิบใน WAL mode**; ต้อง backup-API + integrity_check บน server (ไม่ใช่แค่ byte-size). [[project-bigc-may-payroll]] เคยเจอ "malformed partial" = เคสเดียวกันนี้.

**First real use 29มิ.ย. — SUCCESS, but caught a self-bug first:** the `.ps1` had em-dash `—`
(and would've broken on smart-quotes too) in comments. The server runs **Windows PowerShell 5.1**,
which reads a no-BOM file as the ANSI codepage, so `—` (3 UTF-8 bytes) corrupted the tokenizer →
"string missing terminator" → RESULT FAIL (good: the gate caught it, public stayed 200, no restart).
**Rule: keep `_deploy_remote.ps1` 100% ASCII** (no —, –, ', ', ", "). Dev-side `pwsh` 7 parses it
fine so a local syntax-check won't catch this — grep for bytes >127 instead. `deploy_mvp.sh` echoes
(→ ❌ ✅) are fine (they run in bash on Dev, never sent to PS). Marker tip: avoid `()` in the marker
string (PS arg parsing) — use a plain token like `is_boss`. Second run: all 6 checks PASS, fresh pid
verified, 8020 up, marker present, public 200.
