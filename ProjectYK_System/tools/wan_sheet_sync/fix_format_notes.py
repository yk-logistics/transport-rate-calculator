# -*- coding: utf-8 -*-
"""Jul 26: (1) ก๊อปฟอร์แมตแถวตาราง → 526-547 (2) ขยาย filter ถึง 547
(3) ใส่ note ทุกช่องที่ Claude ใส่ค่า (เทียบกับ backup ก่อน sync)"""
import io, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import gspread
from google.oauth2.service_account import Credentials

KEY = r"C:\Users\guole\Desktop\2026.5.28\Desktop\Project YK\noble-history-446303-e4-c36409a0122c.json"
SP = r"C:\Users\guole\AppData\Local\Temp\claude\C--Users-guole-Desktop-2026-5-28-Desktop-Project-YK\00b15541-c376-485b-b84b-a3a3578678ce\scratchpad"
MAXCOL = 16
NROWS = 547

gc = gspread.authorize(Credentials.from_service_account_file(KEY, scopes=[
    "https://www.googleapis.com/auth/spreadsheets"]))
sh = gc.open_by_key("1F5eJlYsNAGi1zzm1Ej-dlk7Jcp6EEUz8cq1Om4n5VnQ")
ws = sh.worksheet("Jul 26")
sid = ws.id

# ---- (1)+(2) format + filter ----
reqs = [
    # ก๊อปฟอร์แมตทั้งแถวจากแถว 525 (แถวตาราง scaffold ปกติ) ไป 526-547
    {"copyPaste": {
        "source": {"sheetId": sid, "startRowIndex": 524, "endRowIndex": 525,
                   "startColumnIndex": 0, "endColumnIndex": MAXCOL},
        "destination": {"sheetId": sid, "startRowIndex": 525, "endRowIndex": NROWS,
                        "startColumnIndex": 0, "endColumnIndex": MAXCOL},
        "pasteType": "PASTE_FORMAT", "pasteOrientation": "NORMAL"}},
    # ขยาย basic filter คลุมถึงแถว 547 (คง filterSpecs เดิม D,E)
    {"setBasicFilter": {"filter": {
        "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": NROWS,
                  "startColumnIndex": 0, "endColumnIndex": MAXCOL},
        "filterSpecs": [{"columnIndex": 4, "filterCriteria": {}},
                        {"columnIndex": 3, "filterCriteria": {}}]}}},
]
sh.batch_update({"requests": reqs})
print("format+filter applied")

# ---- (3) notes ----
with open(SP + r"\backup_Jul26.json", encoding="utf-8") as f:
    old = json.load(f)  # 525 rows display values ก่อน sync
new_disp = ws.get(f"A1:P{NROWS}")
new_form = ws.get(f"A1:P{NROWS}", value_render_option="FORMULA")

def cell(g, i, j):
    if i >= len(g):
        return ""
    r = g[i]
    return str(r[j]).strip() if j < len(r) else ""

SKIP = {(0, 0), (35, 6)}  # A1 (note แท็บ), G36 (note ทองสุข) — มี note สำคัญอยู่แล้ว
note_cells = {}  # (row0,col0) -> note text
for i in range(1, NROWS):  # ข้ามหัวตาราง
    for j in range(MAXCOL):
        if (i, j) in SKIP:
            continue
        nd = cell(new_disp, i, j)
        nf = cell(new_form, i, j)
        od = cell(old, i, j)
        has_new = nd != "" or nf != ""
        if not has_new:
            continue
        if nd == od and not (nf.startswith("=") and od == ""):
            continue  # ค่าเท่าเดิม
        if od == "":
            note_cells[(i, j)] = "Claude ใส่ช่องนี้ (sync จากไฟล์ Excel พี่หวาน 2/7/2026) — เดิมว่าง"
        else:
            note_cells[(i, j)] = (f"Claude ใส่ช่องนี้ (sync จากไฟล์ Excel พี่หวาน 2/7/2026) — "
                                  f"ค่าก่อน sync: '{od}' (แถวเลื่อนตาม layout ไฟล์ ค่าเดิมไม่หาย)")
print("note cells:", len(note_cells))

# group เป็น run ต่อเนื่องรายแถว → 1 request ต่อ run
note_reqs = []
for i in sorted({k[0] for k in note_cells}):
    cols = sorted(j for (r, j) in note_cells if r == i)
    run = [cols[0]]
    for c in cols[1:]:
        if c == run[-1] + 1:
            run.append(c)
        else:
            note_reqs.append((i, run[0], run[-1]))
            run = [c]
    note_reqs.append((i, run[0], run[-1]))
print("note requests:", len(note_reqs))

requests = []
for i, c0, c1 in note_reqs:
    requests.append({"updateCells": {
        "range": {"sheetId": sid, "startRowIndex": i, "endRowIndex": i + 1,
                  "startColumnIndex": c0, "endColumnIndex": c1 + 1},
        "rows": [{"values": [{"note": note_cells[(i, j)]} for j in range(c0, c1 + 1)]}],
        "fields": "note"}})

# ส่งเป็นก้อนละ 500 requests กัน payload ใหญ่เกิน
for k in range(0, len(requests), 500):
    sh.batch_update({"requests": requests[k:k + 500]})
    print(f"notes batch {k}-{k + len(requests[k:k + 500])} done")

# ---- verify ----
chk = ws.get("A524:P547")
zeros = sum(1 for r in chk for v in r if str(v).strip() == "0")
print("verify rows 524-547: cells displaying '0' =", zeros)
meta = sh.fetch_sheet_metadata()
for s in meta["sheets"]:
    if s["properties"]["sheetId"] == sid:
        print("filter range now:", s.get("basicFilter", {}).get("range"))
print("DONE")
