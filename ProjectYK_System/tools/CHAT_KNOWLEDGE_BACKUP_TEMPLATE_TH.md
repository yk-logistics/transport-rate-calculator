# Chat Knowledge Backup Template (Project YK)

ใช้เทมเพลตนี้ตอนจบงานแต่ละรอบ เพื่อกันความรู้หลุดจากแชต

## 1) Executive Snapshot (คัดลอกแล้วกรอก)

```text
[SESSION BACKUP]
วันที่:
งาน:
ผลลัพธ์ใช้งานได้ทันที:
- ...
- ...
```

## 2) Domain Facts ใหม่จากหน้างาน

```text
[NEW DOMAIN FACTS]
- Site:
  Fact:
  ตัวอย่างจริง:
  ผลกระทบ:
```

## 3) Decisions ที่ล็อกแล้ว

```text
[DECISIONS LOCKED]
- เรื่อง:
  เลือก:
  เหตุผล:
  ทางเลือกที่ไม่เลือก:
```

## 4) Verify + Risk (กันข้อมูลตกหล่น)

```text
[VERIFY & LEAK CHECK]
- unlinked records: <count> รายการ / <amount> บาท
- cycle tag mismatch: <count>
- cross-site name collision: <count>
- source mismatch: <count>
```

## 5) ก่อน-หลัง (ถ้าแก้ logic เงิน)

```text
[BEFORE vs AFTER]
- ตัวชี้วัดหลัก:
  before:
  after:
  diff:
```

## 6) Action ถัดไป (พร้อมทำทันที)

```text
[NEXT ACTIONS]
1) [next] ...
2) [next] ...
3) [blocked] ... (ถ้ามี)
```

## 7) จุดที่ต้องให้โอกดเอง

```text
[MANUAL STEPS]
- ต้องกดหน้า:
- ต้องตรวจค่า:
- เงื่อนไขผ่าน:
```

---

## ใช้ยังไงให้เร็ว

1. กรอกข้อ 1 + 4 ก่อน (กันลืมตัวเลขเสี่ยง)
2. ถ้ามี domain fact ใหม่ ให้กรอกข้อ 2 ทันที
3. แปะส่วนที่เกี่ยวไปอัปเดต `CONTEXT_LOG.md` / `NEXT_ACTION_PLAN.md` / `CHANGELOG_MASTER.md`
