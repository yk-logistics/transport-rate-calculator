"""วินิจฉัย: กลุ่มไหน forward ไม่เข้า Discord (read-only)
รันบน server:  .venv\Scripts\python.exe diag_forward.py
"""
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
db = Path(__file__).parent / "line_archive.db"
c = sqlite3.connect(db)
c.row_factory = sqlite3.Row

print("=" * 70)
print("ทุกกลุ่ม: ข้อความทั้งหมด / forward แล้ว / ยังค้าง / channel id")
print("=" * 70)
rows = c.execute("""
    SELECT g.group_id, g.name, g.discord_channel_id AS ch, g.category,
           COUNT(m.id) AS total,
           SUM(CASE WHEN m.discord_forwarded=1 THEN 1 ELSE 0 END) AS fwd,
           SUM(CASE WHEN m.discord_forwarded=0 THEN 1 ELSE 0 END) AS pending,
           MAX(m.sent_at) AS last_msg
    FROM line_group g
    LEFT JOIN line_message m ON m.group_id = g.group_id
    GROUP BY g.group_id
    ORDER BY pending DESC, total DESC
""").fetchall()

for r in rows:
    flag = ""
    if r["ch"] is None:
        flag = "  <-- ไม่มี channel_id!"
    elif r["total"] == 0:
        flag = "  <-- channel มี แต่ 0 ข้อความ (event ไม่มาถึง?)"
    elif r["pending"] and r["pending"] == r["total"]:
        flag = "  <-- มีข้อความแต่ forward ค้างทั้งหมด!"
    elif r["pending"]:
        flag = f"  <-- ค้าง {r['pending']}"
    print(f"[{r['total']:4} msg | fwd {r['fwd'] or 0:4} | pend {r['pending'] or 0:4}] "
          f"ch={'YES' if r['ch'] else 'NONE':4} | {r['name'] or '(no name)'}{flag}")

print()
print("=" * 70)
print(">>> กลุ่มที่ยังไม่มีข้อความเลย (0 msg) <<<")
print("=" * 70)
zero_all = [r for r in rows if r["total"] == 0]
for r in zero_all:
    print(f"  - {r['name'] or '(no name)'}   [ch={'YES' if r['ch'] else 'NONE'}]")
if not zero_all:
    print("  (ไม่มี - ทุกกลุ่มมีข้อความครบ)")

print()
print("=" * 70)
print("สรุป")
print("=" * 70)
no_ch = [r for r in rows if r["ch"] is None]
zero = [r for r in rows if r["ch"] and r["total"] == 0]
stuck = [r for r in rows if r["total"] and r["pending"] == r["total"]]
print(f"กลุ่มไม่มี channel_id           : {len(no_ch)}")
print(f"กลุ่มมี channel แต่ 0 ข้อความ   : {len(zero)}")
print(f"กลุ่มมีข้อความแต่ forward ค้างหมด: {len(stuck)}")
print(f"รวมทุกกลุ่ม                     : {len(rows)}")
