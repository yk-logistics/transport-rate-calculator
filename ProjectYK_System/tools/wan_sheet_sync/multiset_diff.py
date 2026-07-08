# -*- coding: utf-8 -*-
"""Multiset row diff (cols 1-11 = trip content, ignore fuel cols 12-16) xlsx vs gsheet.
Also fuel-cols-only multiset (cols 1-4 + 12-16) to catch fuel rows พี่หวาน added."""
import gspread, datetime
from collections import Counter
from google.oauth2.service_account import Credentials
import openpyxl

KEY = r"C:\Users\guole\Desktop\2026.5.28\Desktop\Project YK\noble-history-446303-e4-c36409a0122c.json"
TARGET_ID = "1F5eJlYsNAGi1zzm1Ej-dlk7Jcp6EEUz8cq1Om4n5VnQ"
XLSX = r"C:\Users\guole\AppData\Local\Temp\claude\C--Users-guole-Desktop-2026-5-28-Desktop-Project-YK\00b15541-c376-485b-b84b-a3a3578678ce\scratchpad\wan_file.xlsx"
LOG = r"C:\Users\guole\AppData\Local\Temp\claude\C--Users-guole-Desktop-2026-5-28-Desktop-Project-YK\00b15541-c376-485b-b84b-a3a3578678ce\scratchpad\mset_log.txt"

out = open(LOG, "w", encoding="utf-8")
def p(*a):
    print(*a, file=out)

def norm(v):
    if v is None:
        return ""
    if isinstance(v, (datetime.datetime, datetime.date)):
        return f"{v.day}/{v.month}/{v.year}"
    if isinstance(v, float) and v == int(v):
        v = int(v)
    s = str(v).strip().replace(",", "")
    try:
        f = float(s)
        if abs(f) < 0.001:
            return ""
        return str(round(f, 1))
    except ValueError:
        return s

gc = gspread.authorize(Credentials.from_service_account_file(KEY, scopes=[
    "https://www.googleapis.com/auth/spreadsheets.readonly"]))
sh = gc.open_by_key(TARGET_ID)
wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)

def load(name):
    xrows = []
    for row in wb[name].iter_rows(min_row=1, max_col=16, values_only=True):
        xrows.append([norm(v) for v in row])
    grows = []
    for r in sh.worksheet(name).get_all_values():
        r = list(r[:16]) + [""] * (16 - len(r[:16]))
        grows.append([norm(v) for v in r])
    return xrows, grows

def trip_key(r):
    # cols 1-8,10,11 (skip col9 เลขที่/invoice which system side fills; skip fuel 12-16)
    return tuple(r[0:8] + r[9:11])

def fuel_key(r):
    # date,plate,driver + fuel cols 13-16 (mile,liters,price,amount,station)
    return tuple(r[0:2] + r[3:4] + r[11:16])

def has_content(k):
    return any(v not in ("", "0") for v in k)

def report(name):
    xrows, grows = load(name)
    p(f"########## {name}: gsheet={len(grows)} xlsx={len(xrows)} ##########")
    for label, keyf in [("TRIP(cols1-8,10,11)", trip_key), ("FUEL(date,plate,driver,cols12-16)", fuel_key)]:
        xc = Counter(keyf(r) for r in xrows if has_content(keyf(r)))
        gc_ = Counter(keyf(r) for r in grows if has_content(keyf(r)))
        only_x = xc - gc_
        only_g = gc_ - xc
        p(f"--- {label}: xlsx-only={sum(only_x.values())} gsheet-only={sum(only_g.values())}")
        p("  [xlsx-only = พี่หวานคีย์เพิ่ม/แก้ ยังไม่อยู่ในชีทจริง]")
        for k, n in only_x.items():
            p(f"   +{n}x", " | ".join(k))
        p("  [gsheet-only = อยู่ในชีทจริงแต่ไม่อยู่ในไฟล์พี่หวาน (อาจโดนแก้/จะหายถ้า replace)]")
        for k, n in only_g.items():
            p(f"   -{n}x", " | ".join(k))
    p("")

for tab in ["Jun 26", "Jul 26"]:
    report(tab)
out.close()
print("done")
