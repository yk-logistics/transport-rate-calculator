---
name: reference-cdp-browser-test
description: "Drive real Chrome headless to test interactive JS/Tabulator behavior (clicks, freeze, edits) without Playwright/Selenium — stdlib websockets + CDP"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 88db0e66-531a-4800-8509-a9c2e30dcb98
---

ทดสอบ JS โต้ตอบจริง (Tabulator freeze/edit, คลิกเมนู) ได้โดยไม่ต้องลง Playwright/Selenium (ไม่มีในเครื่อง) — ขับ Chrome headless ผ่าน DevTools Protocol (CDP) ด้วย `websockets` (มีใน venv อยู่แล้ว).

**สูตร (scratchpad/cdp_freeze.py เป็นตัวอย่าง):**
1. ตั้ง app ทดสอบบนพอร์ตว่าง: launcher patch `auth.current_user=lambda req: FakeU(role=admin)` แล้ว `uvicorn.run(main.app, port=8011)` (bg) + `YK_INSECURE_COOKIES=1` + DATABASE_URL ชี้ DB ก๊อป
2. `subprocess.Popen([CHROME, "--headless=new", "--remote-debugging-port=9223", "--user-data-dir=<tmp>", "--no-first-run", "--disable-gpu", URL])`
3. หา ws target: `GET http://127.0.0.1:9223/json` → `webSocketDebuggerUrl` ของ type=page
4. `websockets.connect(ws_url, max_size=None)`; ส่ง `{"id","method":"Runtime.evaluate","params":{"expression":..,"returnByValue":True}}`
5. รอ table พร้อม: poll `Tabulator.findTable('#sel')[0].getColumns().length>0`
6. อ่าน state: `getColumns().map(c=>({f:c.getField(),z:!!c.getDefinition().frozen,vis:c.isVisible()}))`
7. จำลอง user จริง: dispatch `MouseEvent('contextmenu',{clientX,clientY})` บน header แล้วหา menu item ด้วย textContent regex → `mousedown` (อย่าเรียกฟังก์ชันใน closure IIFE ตรงๆ = เข้าไม่ถึง)

**GOTCHA:** `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` ก่อน print (emoji/ไทยใน menu ทำ cp1252 crash); CHROME=`C:\Program Files\Google\Chrome\Application\chrome.exe`; ลบ user-data-dir tmp ทุกครั้ง (ไม่งั้น localStorage ค้างข้ามรัน — แต่ก็ใช้พิสูจน์ persistence ได้); kill app 8011 by port PID + chrome เมื่อเสร็จ.

ใช้ครั้งแรก 30มิ.ย. พิสูจน์ [[project-daily-grid-save-auth-redirect]] freeze fix (setColumns rebuild) — แทนการ "ยืนยันทางอ้อม" ที่เคย ship บั๊กไป 2 รอบ. เกี่ยว [[reference-chrome-headless-pdf]] (Chrome headless สำหรับ PDF — คนละงานแต่ binary เดียวกัน).
