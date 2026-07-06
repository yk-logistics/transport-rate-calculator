---
name: project-tradelab-paper-bot
description: "TradeLab บอทเทรดเงินสมมุติของโอ (นอก repo YK) — C:\\Users\\guole\\Desktop\\TradeLab, port 8030, เริ่ม 5 ก.ค. 2026"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9fdb7aae-8871-4b00-b866-2b25cf12aac0
---

โปรเจกต์ส่วนตัวโอ (passive income) **แยกจาก repo YK สิ้นเชิง**

**🌐 ตัวจริงรันบน server แล้ว (ย้าย 5 ก.ค. บ่าย): https://trade.yklogistics.uk** — Basic auth (รหัสใน `TradeLab\auth.txt` เครื่องบ้าน — ห้าม commit); server path `C:\Users\yklog\TradeLab\` + task `YK_TRADELAB` (SYSTEM ONSTART); เพิ่ม ingress trade→8030 ใน tunnel `yk-line` (backup `config.yml.bak_before_trade`); **gotcha: restart tunnel แล้ว process เก่าอาจไม่ตาย → เช็ค Get-Process cloudflared เหลือตัวเดียว ไม่งั้น hostname ใหม่ 404**; เครื่องบ้าน `C:\Users\guole\Desktop\TradeLab\` = dev copy ปิดถาวร (schtask ลบแล้ว) ห้ามรันคู่

- **เป้าหมาย:** พิสูจน์ด้วยตัวเลขว่าบอทเทรดชนะ "ซื้อถือเฉยๆ" ได้จริงไหม ก่อนคิดเรื่องเงินจริง/ซื้อเครื่อง (ผมแนะนำโอไปแล้ว 5 ก.ค.: อย่าเพิ่งซื้อคอม 300-500k มาเทรน LLM เทรด — RAM/GPU แพงผิดปกติถึงปลาย 2027 + สถิติ day trader ~1% เท่านั้นที่ชนะยั่งยืน)
- **สเปค v1:** stdlib Python ล้วน (ไม่มี pip deps), เงินสมมุติ 100k แบ่ง 5 เหรียญ BTC/ETH/XRP/ADA/DOGE เหรียญละ 20k, ราคาจริง Bitkub public API, สูตร SMA 12h/48h crossover รายชั่วโมง, fee 0.25%/ฝั่ง, ลูป 15 นาที, dashboard `http://localhost:8030` (รีเฟรชเอง 60 วิ)
- **ข้อมูล:** `tradelab.db` (SQLite) — decisions ทุกรอบ + trades + snapshots (bot_equity vs hold_equity คู่เทียบ buy&hold ตั้ง baseline ราคารอบแรก)
- **เริ่มพอร์ต:** 5 ก.ค. 2026 09:31 — รอบแรกซื้อครบ 5 เหรียญ (fast>slow ทุกตัว) เหลือ 99,750 หลังหัก fee
- **เปิด/ปิด (ทำแล้ว 5 ก.ค.):** Task Scheduler "TradeLab" ONLOGON (pythonw ไม่มีหน้าต่าง) = เปิดเครื่องบอทตื่นเอง; หน้าเว็บมีปุ่ม ⏸ พักเทรด (meta.paused, ยัง snapshot ต่อ) + ⛔ ปิดโปรแกรม + ชีพจร "รอบล่าสุด x นาทีที่แล้ว" (แดงถ้า >40 นาที); stop.bat kill ตาม PID ของ port 8030
- **เกณฑ์ตัดสิน:** ดู 1-3 เดือน บอทชนะ hold หลังหัก fee → ค่อยคุยขั้นถัดไป; แพ้ → บทเรียนฟรี
- **🚦 เกตเงินจริง:** อยู่ใน `TradeLab\RUNBOOK.md` (เขียนไว้ให้ Opus/Sonnet ดูแลต่อหลัง Fable หมด 7 ก.ค.) — เฟส 2 เงินจริงต้อง: ผ่านเฟส 1 ก่อน + ก้อนเล็ก 5-10k + key จำกัดสิทธิ์ปิดถอนเงิน + hard stop + ตัวหลักทำเองห้าม delegate; **ห้ามให้ความหวังเกินจริง — ระบบนี้มีไว้หาคำตอบ ไม่ใช่ยืนยันความหวัง**
- **พอร์ตหุ้นสหรัฐ paper เพิ่มแล้ว 5 ก.ค.** (โอเล่นหุ้น US จริง): $3,000 แบ่ง 5 ตัว default AAPL/MSFT/NVDA/GOOGL/TSLA — **รอโอส่งรายชื่อหุ้นที่ถือจริงมาสลับ**; Yahoo รายวัน SMA 10/30d ตัดสินใจวันละครั้ง; DB ใช้ prefix `US:` (cash_thb=USD!) + us_snapshots; รอบแรกทุกตัว fast<slow → ถือเงินสด ไม่ซื้อ = ตัวอย่างสด "หลบขาลง"
- **แผนต่อ (ยังไม่ทำ):** เสียบ LLM อ่านข่าววันละ 2-4 รอบ; สูตรที่ 2 มี short แข่ง long-only (โอถาม 5 ก.ค.); หุ้นไทย `.BK` (ต้องล็อต 100+คอม 0.15-0.25%+VAT); เงินจริงสหรัฐ=Alpaca/IBKR, หุ้นไทยไม่มี API → บอทส่งสัญญาณ LINE/Discord ให้โอกดมือ
- gotcha: console Windows พิมพ์ไทยต้อง `$env:PYTHONIOENCODING='utf-8'` ก่อนรัน python inline

เกี่ยวข้อง: [[reference-qwen-subagent]] (ถ้าจะเสียบ Qwen อ่านข่าว), [[feedback-concise-no-code-dump]]
