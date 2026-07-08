# -*- coding: utf-8 -*-
"""Download พี่หวาน's xlsx from Drive + list target gsheet tabs."""
import io, json, sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

KEY = r"C:\Users\guole\Desktop\2026.5.28\Desktop\Project YK\noble-history-446303-e4-c36409a0122c.json"
FILE_ID = "1vQ0l2RtppdDsBDorKMZaCyEBJ6sJKRrf"
TARGET_ID = "1F5eJlYsNAGi1zzm1Ej-dlk7Jcp6EEUz8cq1Om4n5VnQ"
OUT = r"C:\Users\guole\AppData\Local\Temp\claude\C--Users-guole-Desktop-2026-5-28-Desktop-Project-YK\00b15541-c376-485b-b84b-a3a3578678ce\scratchpad\wan_file.xlsx"
LOG = r"C:\Users\guole\AppData\Local\Temp\claude\C--Users-guole-Desktop-2026-5-28-Desktop-Project-YK\00b15541-c376-485b-b84b-a3a3578678ce\scratchpad\dl_log.txt"

out = open(LOG, "w", encoding="utf-8")
def p(*a):
    print(*a, file=out)

scopes = ["https://www.googleapis.com/auth/drive.readonly",
          "https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = Credentials.from_service_account_file(KEY, scopes=scopes)
drive = build("drive", "v3", credentials=creds)

meta = drive.files().get(fileId=FILE_ID, fields="name,mimeType,modifiedTime,size").execute()
p("META:", json.dumps(meta, ensure_ascii=False))

if meta["mimeType"] == "application/vnd.google-apps.spreadsheet":
    req = drive.files().export_media(fileId=FILE_ID,
        mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    req = drive.files().get_media(fileId=FILE_ID)

buf = io.FileIO(OUT, "wb")
dl = MediaIoBaseDownload(buf, req)
done = False
while not done:
    _, done = dl.next_chunk()
buf.close()
p("downloaded ->", OUT)

import gspread
gc = gspread.authorize(Credentials.from_service_account_file(KEY, scopes=[
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"]))
sh = gc.open_by_key(TARGET_ID)
p("TARGET title:", sh.title)
for ws in sh.worksheets():
    p("  tab:", ws.title, ws.row_count, "x", ws.col_count)

out.close()
print("done")
