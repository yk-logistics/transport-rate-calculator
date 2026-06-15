---
name: reference-yklogistics-dns
description: DNS records ของ yklogistics.com ก่อนย้ายไป Cloudflare — หลักฐานกันอีเมลล่ม
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7b25737d-55e4-4ec9-afd0-a60395c57606
---

โดเมน `yklogistics.com` ของโอ (มีอีเมลใช้งานจริง — **ห้ามล่ม**) ก่อนย้าย nameserver ไป Cloudflare สำหรับ named tunnel ของ [[reference-line-archiver]].

**Nameserver เดิม:** `cloudcs1.24webhost.com`, `cloudcs2.24webhost.com` (ผ่าน cPanel / 24webhost)

**DNS records ที่ต้องมีครบหลังย้าย (snapshot 2026-06-12):**

| Type | Name | Value |
|------|------|-------|
| A | yklogistics.com | `5.223.56.39` |
| MX | yklogistics.com | `0 yklogistics.com` |
| TXT (SPF) | yklogistics.com | `v=spf1 +a +mx +ip4:5.223.56.39 ~all` |

อีเมลวิ่งไปเซิร์ฟเวอร์ hosting ที่ IP `5.223.56.39`. ถ้าย้าย NS ไป Cloudflare แล้ว ต้องตรวจว่า Cloudflare import 3 record นี้ครบ — โดยเฉพาะ MX + SPF (TXT) ขาดเมื่อไหร่อีเมลล่มทันที. เพิ่ม `line.yklogistics.com` (CNAME → tunnel) สำหรับ archiver โดยไม่แตะ 3 record ข้างบน.
