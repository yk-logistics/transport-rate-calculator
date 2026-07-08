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
- **🇺🇸 พอร์ตกระจก Webull โอ (6 ก.ค. เย็น — แทน US paper 5 หุ้นเทคเดิมที่ถูกถอด):** โอส่งรูปพอร์ตจริง 18 ตัว ($5,192.78 เช็คยอดรวมตรง = ครบไม่มีตกจอ; qty+ทุนอยู่ใน `MIRROR_SEED` ใน main.py) → บอท v2 daily บริหารเงินสมมุติเทียบ "ถือเฉยๆ แบบโอ"; ตาราง us_mirror/us_mirror_snapshots + prefix `OA:` (value_thb=USD); **หลักคิดสำคัญ: entry นับจากราคาวันแรกที่บอทเห็น ไม่ใช่ทุนเก่าโอ** (ลองอิงทุนเก่าแล้วบอทเทขาย 11/18 วันแรกโดยไร้สัญญาณเดินหน้า — แก้แล้วเหลือขายจริง 4 ตัวมีเหตุผล); **backtest_us.py บอกชัด: หุ้นสายจรวดชุดนี้ hold ชนะบอททุกหน้าต่าง (2ปี +301% vs +94%, 1ปี +27 vs +11, 6ด +2.9 vs −1.1) — โอรับทราบแล้วเลือก "สมอง v2 เต็มระบบ" เพื่อพิสูจน์เดินหน้า**; ถามโอผ่านการ์ดก่อนเปิดตามกติกา backtest-แพ้-ต้องถาม
- **🧠 v2 deploy แล้ว 6 ก.ค. 17:09 (โอสั่ง "จัดเต็ม" หลังเห็น v1 ขายตอนตก):** พอร์ตแยกอีก 100k แข่ง 3 ทาง v1/v2/hold — regime switch (ADX≥25 เทรนด์=เส้นตัด+กันชน 0.3% / ต่ำ=ช้อนกรอบ Bollinger+RSI≤32 แต่กรอบต้องกว้าง≥2.5%) + trailing stop 6×ATR (เบรกฉุกเฉิน — แคบกว่านี้โดนสะบัด, จูนจาก backtest) + พักซื้อ 12 ชม.หลังขาย + veto ชั้น F&G (≥80 งดซื้อ ≤20 ผ่อน RSI≤40) + AI อ่านข่าว RSS วันละ 2 รอบ 07/19น. (Qwen→Claude haiku fallback — **รอบแรก Qwen ล่มจริง fallback claude สำเร็จ**); สเปค `TradeLab\DESIGN_V2.md`; **backtest ชนะ/เสมอ v1 ทั้ง 3 หน้าต่าง** (60วัน: hold −24%/v1 −9%/v2 −1.3% · 35วัน: +3.7 เท่า v1 · 14วัน: +7.8 ชนะ v1 +4.3); secrets ใน `C:\Users\yklog\TradeLab\ai.env` (คัดจาก start_mvp.bat, ไม่มีไฟล์=ข้ามชั้นข่าว); ตาราง v2_positions/v2_snapshots/senti + prefix `V2:` ใน trades/decisions; `backtest.py` รันซ้ำได้ (`python backtest.py 35`)
- **gotcha Discord ไทยเพี้ยน:** ข้อความทดสอบแรกเป็น mojibake เพราะเขียน .ps1 (UTF-8 ไม่มี BOM) ที่มี here-string ไทย → PowerShell 5.1 อ่านเป็น ANSI — **ห้ามฝังไทยใน .ps1 ส่งไปรัน; ให้ scp ไฟล์ .py ตรงแล้วรันด้วย python แทน**; ตัวบอทเอง (main.py) ส่งไทยถูกต้องเพราะ json.dumps escape เป็น ASCII อยู่แล้ว
- **รอบปรับปรุง 6 ก.ค. เย็น (โอสั่ง "ดูอีกทีมีอะไรดีขึ้นได้"):** ① ซ่อม Qwen บนเซิร์ฟเวอร์ — **gotcha: ai.env สร้างด้วย PowerShell มี BOM ทำให้ตัวแปรบรรทัดแรกอ่านไม่ออก** (โค้ดอ่านด้วย utf-8-sig แล้ว; อาการ = fallback claude ทั้งที่คีย์อยู่) ② กราฟแข่ง 3 เส้นสนามเดียว (ทุกเส้น=100 ณ เริ่ม v2) บนการ์ด v2 ③ สรุปรายวันเข้า Discord 20:00 (`run_digest_cycle`, webhook ช่องเดียวกับ PowerAlert — URL อยู่ `C:\YK_PowerAlert\discord_webhook.txt`, ต่อเข้า ai.env แล้ว) ④ `watchdog.py` + task `YK_TRADELAB_WATCHDOG` ทุก 30 นาที: บอทเงียบ >40 นาที → ปลุกเอง + แจ้ง Discord (กันตายเงียบแบบตัว Desktop) ⑤ ทดลอง "BTC filter บล็อกซื้อเหรียญเล็กตอน BTC ขาลง" — **ตัดทิ้ง**: ช่วยขาลง (−1.24→−0.04%) แต่ทำร้ายขาเด้ง (+7.89→+6.00%) ไม่ robust
- **แผนต่อ (ยังไม่ทำ):** สูตรที่ 2 มี short แข่ง long-only (โอถาม 5 ก.ค.); v2 ฝั่งหุ้นสหรัฐ; สกอร์บอร์ดแยกกำไรรายชั้นกติกา; หุ้นไทย `.BK` (ต้องล็อต 100+คอม 0.15-0.25%+VAT); เงินจริงสหรัฐ=Alpaca/IBKR, หุ้นไทยไม่มี API → บอทส่งสัญญาณ LINE/Discord ให้โอกดมือ
- gotcha: console Windows พิมพ์ไทยต้อง `$env:PYTHONIOENCODING='utf-8'` ก่อนรัน python inline

เกี่ยวข้อง: [[reference-qwen-subagent]] (ถ้าจะเสียบ Qwen อ่านข่าว), [[feedback-concise-no-code-dump]]
