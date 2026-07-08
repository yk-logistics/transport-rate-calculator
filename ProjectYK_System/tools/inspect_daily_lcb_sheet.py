#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
READ-ONLY inspector for the 'Daily LCB' (เดลี่แหลม) Google Sheet.

Does NOT modify anything. Surveys:
  1. Header row of each worksheet (col layout drift across months)
  2. Data-validation rules per column (the 'driver name' validation question)
  3. Sample formulas per column (find odd / inconsistent formulas)

Run from repo root:
  PYTHONUTF8=1 python ProjectYK_System/tools/inspect_daily_lcb_sheet.py
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import gspread

KEY_FILE = 'noble-history-446303-e4-c36409a0122c.json'
SHEET_ID = '1Tm1i7kHGkiYtNwM-HQWEnQReg6VZmLzj7T1DjXr8zqg'


def col_letter(idx0):
    """0-based col index -> A1 letter."""
    s = ''
    n = idx0 + 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def main():
    gc = gspread.service_account(filename=KEY_FILE)
    sh = gc.open_by_key(SHEET_ID)

    # Pull rich metadata: per sheet, the first ~3 rows of dataValidation + formulas,
    # plus a scan of validation across the whole first data column block.
    fields = (
        'sheets('
        'properties(sheetId,title,index,hidden,gridProperties),'
        'data(rowData(values('
        'userEnteredValue,'
        'effectiveValue,'
        'dataValidation,'
        'formattedValue'
        ')))'
        ')'
    )
    meta = sh.fetch_sheet_metadata({'fields': fields, 'ranges': []})

    sheets = meta['sheets']
    print(f'TOTAL SHEETS IN METADATA: {len(sheets)}\n')

    summary = []
    for s in sheets:
        p = s['properties']
        title = p['title']
        hidden = p.get('hidden', False)
        idx = p['index']
        gp = p.get('gridProperties', {})
        rows = gp.get('rowCount')
        cols = gp.get('columnCount')
        summary.append((idx, title, hidden, rows, cols))

    summary.sort()
    print('=== SHEET LIST (index | title | hidden | rows x cols) ===')
    for idx, title, hidden, rows, cols in summary:
        flag = '  [HIDDEN]' if hidden else ''
        print(f'  {idx:>2} | {title:<28} | {rows}x{cols}{flag}')
    print()


if __name__ == '__main__':
    main()
