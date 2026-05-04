# Google Drive Sync Setup (Phase 2)

ใช้ไฟล์นี้เพื่อเปิดโหมด Sync อัตโนมัติระหว่าง PC และ iPhone ผ่าน Google Apps Script

## 1) สร้าง Apps Script

1. เปิด [script.new](https://script.new)
2. วางโค้ดด้านล่างแทนโค้ดเดิมทั้งหมด
3. แก้ค่า `FILE_NAME` และ `SECRET_TOKEN` ตามต้องการ
4. กด Deploy > New deployment > Web app
5. Execute as: `Me`
6. Who has access: `Anyone`
7. Copy Web app URL ไปใส่ในช่อง `Apps Script Web App URL` ในหน้าเครื่องมือ

```javascript
const FILE_NAME = 'yk-cost-data.json';
const SECRET_TOKEN = 'YK_SYNC_2026_LCB_9173';

function getOrCreateFile_() {
  const files = DriveApp.getFilesByName(FILE_NAME);
  if (files.hasNext()) return files.next();
  return DriveApp.createFile(FILE_NAME, JSON.stringify({ records: [] }, null, 2), MimeType.PLAIN_TEXT);
}

function doGet(e) {
  const p = (e && e.parameter) ? e.parameter : {};
  const action = (p.action || '').toLowerCase();
  const secret = p.secret || '';
  if (action === 'ping') return json_({ ok: true, service: 'yk-drive-sync', ts: new Date().toISOString() });
  if (secret !== SECRET_TOKEN) return json_({ ok: false, error: 'unauthorized' });
  if (action !== 'load') return json_({ ok: false, error: 'invalid action' });

  const file = getOrCreateFile_();
  const text = file.getBlob().getDataAsString() || '{"records":[]}';
  return ContentService
    .createTextOutput(text)
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  if (!e || !e.postData || !e.postData.contents) return json_({ ok: false, error: 'missing postData' });
  let body = {};
  try {
    body = JSON.parse(e.postData.contents || '{}');
  } catch (err) {
    return json_({ ok: false, error: 'invalid json' });
  }
  if ((body.secret || '') !== SECRET_TOKEN) return json_({ ok: false, error: 'unauthorized' });
  const action = (body.action || '').toLowerCase();
  if (action === 'resolve_map') {
    const shortUrl = body.shortUrl || '';
    if (!shortUrl) return json_({ ok: false, error: 'missing shortUrl' });
    try {
      const resolvedUrl = resolveMapUrl_(shortUrl);
      return json_({ ok: true, resolvedUrl: resolvedUrl || shortUrl });
    } catch (err) {
      return json_({ ok: false, error: 'resolve failed', detail: String(err) });
    }
  }
  if (action !== 'save') return json_({ ok: false, error: 'invalid action' });

  const payload = body.payload || { records: [] };
  const file = getOrCreateFile_();
  file.setContent(JSON.stringify(payload, null, 2));
  return json_({ ok: true, savedAt: new Date().toISOString(), count: (payload.records || []).length });
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function resolveMapUrl_(url) {
  // 1) follow redirect chain manually (best effort)
  const redirected = resolveShortUrl_(url, 8);
  // 2) if still short URL, try reading HTML and extract canonical/og:url
  if (/^https?:\/\/maps\.app\.goo\.gl\//i.test(redirected || '')) {
    const htmlResp = UrlFetchApp.fetch(redirected, { followRedirects: true, muteHttpExceptions: true });
    const html = htmlResp.getContentText() || '';
    const og = matchFirst_(html, /property=["']og:url["'][^>]*content=["']([^"']+)["']/i);
    if (og) return og;
    const canonical = matchFirst_(html, /rel=["']canonical["'][^>]*href=["']([^"']+)["']/i);
    if (canonical) return canonical;
    return redirected;
  }
  return redirected;
}

function resolveShortUrl_(url, maxHops) {
  let current = url;
  for (let i = 0; i < maxHops; i++) {
    const resp = UrlFetchApp.fetch(current, { followRedirects: false, muteHttpExceptions: true });
    const headers = resp.getAllHeaders();
    const location = headers.Location || headers.location || '';
    if (!location) return current;
    if (/^https?:\/\//i.test(location)) {
      current = location;
    } else {
      // รองรับกรณี redirect เป็น relative path
      const base = current.replace(/^(https?:\/\/[^\/]+).*/, '$1');
      current = base + location;
    }
  }
  return current;
}

function matchFirst_(text, regex) {
  const m = String(text || '').match(regex);
  return (m && m[1]) ? m[1] : '';
}
```

## 2) การใช้งานในหน้า HTML

1. ใส่ URL ที่ได้จาก Deploy ลงใน `Apps Script Web App URL`
2. ใส่ `Secret` ให้ตรงกับ `SECRET_TOKEN`
3. กด `Sync to Drive` เพื่ออัปโหลดข้อมูลล่าสุด
4. อีกเครื่องกด `Load from Drive` เพื่อดึงข้อมูลชุดเดียวกัน

## 3) หมายเหตุ

- ถ้าปรับโค้ด Apps Script ต้อง Deploy เวอร์ชันใหม่
- ถ้าได้ `unauthorized` ให้เช็ค Secret ทั้งสองฝั่ง
- ถ้า CORS error ให้ลองเปิด/ปิดแท็บใหม่ และยืนยันว่าใช้ URL ของ Web app (ลงท้าย `/exec`)
