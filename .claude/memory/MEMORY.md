# Memory Index

- [MVP test plan](project-mvp-test-plan.md) — โอทดสอบ MVP end-to-end (เริ่ม 2026-06-10); เปิดด้วย `MVP S<n> ทำต่อ` → อ่าน docs/MVP_TEST_PLAN.md; ground truth ที่ Work\Salary\2026\5.May\LCB
- [Test-data cleanup safety](feedback-test-data-cleanup-safety.md) — ลบ test row ที่ POST เข้า app.db จริง ต้องลบด้วย id ที่ได้คืน ห้ามลบด้วย filter (work_date/...) เพราะชนข้อมูลจริง — เคยลบงานจริง 3 แถวต้องกู้จาก backup
- [Claude Code multiple installs](claude-code-multiple-installs.md) — which `claude` actually runs on โอ's machine + how updates / model-picker versions work
- [Qwen subagent pattern](reference-qwen-subagent.md) — offload read-only recon/summarize to cheap Qwen via _Claude Tools/qwen.ps1; safety is by discipline (no technical guardrail)
- [Delegation preference](feedback-qwen-and-subagent-cost.md) — keep MAIN context small first; delegate bulky reads aggressively (free Qwen preferred, native subagents OK), keep synthesis/decisions in main
- [Auto-resume system](reference-auto-resume-system.md) — overnight resume-after-limit: SessionStart hook + ~/.claude watcher; cap/log/arm files; UTF-8 BOM rule
- [Oatside billing recon](project-oatside-billing-recon.md) — monthly daily↔GPS: BH/ตีเปล่า=manual_return 50%, demurrage system≥keyer rule, no_finish uses waiting-day rate; scripts + file layout
- [Oatside report UI edits](project-oatside-report-ui-edits.md) — change report HTML without moving billing numbers: edit builder + patch existing HTML (rebuild re-picks newest GPS → numbers shift)
- [Superpowers + 9arm models](project-superpowers-9arm-models.md) — install superpowers in main Claude (auto+confirm, subagents→Sonnet); 9arm free-Qwen is a SEPARATE config dir w/ no plugins, can't host superpowers, never run money work on it
- [Makcu macro_engine.py](reference-makcu-macro-engine.md) — โอ's personal KM-macro tool at `_NonYK_Projects\makcu\` (NOT in YK repo); migrating Makcu→Waveshare RP2350-USB-A via same km.* serial protocol
- [LINE archiver](reference-line-archiver.md) — เก็บข้อความ+รูปกลุ่ม LINE ลง SQLite/Discord; service แยก port 8020; start_all.bat; tunnel = Cloudflare (quick→named line.yklogistics.com)
- [yklogistics.com DNS](reference-yklogistics-dns.md) — DNS snapshot ก่อนย้าย Cloudflare; A/MX/SPF ที่ห้ามหาย (อีเมลใช้จริง ห้ามล่ม)
- [SSH to YK machine](reference-ssh-to-yk-machine.md) — passwordless SSH from Home/.178 → YK/.197 (user yklog); admin keys file; LAN-only, plan Tailscale for off-LAN
- [MVP server deploy](reference-mvp-server-deploy.md) — MVP live at app.yklogistics.uk (copy-folder deploy, Py3.12 venv, unattended boot tasks, RBAC login yk1/changeme1); deploy_mvp_to_server.sh; runbook MVP_SERVER_DEPLOY.md
