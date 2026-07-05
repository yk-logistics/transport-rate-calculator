// Service worker ขั้นต่ำ — มีไว้ให้ Chrome ถือว่าเว็บ "ติดตั้งได้" (installable)
// จงใจไม่ cache อะไร: fetch ตรงจาก network เสมอ กันปัญหาไฟล์เก่าค้างหลัง deploy.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => { /* passthrough: ปล่อยให้ browser จัดการเอง */ });
