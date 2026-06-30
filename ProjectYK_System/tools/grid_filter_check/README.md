# Grid header-filter regression check

Headless-Chrome repro that reproduced + proved the fix for the daily-grid
Excel-style header filter bug (เปลี่ยน filter จากชุดนึงไปอีกชุดโดยไม่ล้างก่อน → ไม่ apply).

**Root cause:** Tabulator 6.x custom header-filter editor calls `success(value)` to set the
filter value, but the table does NOT re-run row filtering when `success()` is called again with
a new value back-to-back (A→B) — only when the filter passes through empty/`null` (clear/ALL).
**Fix:** call `table.refreshFilter()` right after `success()` in `applyFilter()`
(see `templates/daily_grid.html`).

## Run (Windows)

```bash
CH="/c/Program Files/Google/Chrome/Application/chrome.exe"
DIR="$(pwd)/ProjectYK_System/tools/grid_filter_check"
# vendored tabulator next to the html (download once):
curl -s "https://unpkg.com/tabulator-tables@6.2.1/dist/js/tabulator.min.js"  -o "$DIR/tabulator.min.js"
curl -s "https://unpkg.com/tabulator-tables@6.2.1/dist/css/tabulator.min.css" -o "$DIR/tabulator.min.css"
# fix ON (default) -> ALL_PASS ; add #nofix to the URL -> SOME_FAIL (shows the bug)
"$CH" --headless=new --disable-gpu --no-sandbox --user-data-dir="$DIR/_cudd" \
  --virtual-time-budget=12000 --window-size=820,440 --screenshot="$DIR/out.png" \
  "file:///C:/.../grid_filter_check/grid_filter_repro.html"
```

Read `out.png`: the big line shows `FIX=true ALL_PASS` (fixed) or `FIX=false SOME_FAIL` (bug).
5 sequences tested: A→B, clear→all, ALL−C, {A,B}→{A,C}, C→A.

Note: the repro carries a COPY of `makeExcelFilter`/`excelFilterFunc`. If that logic in
`daily_grid.html` changes materially, re-sync the copy. Chrome `file://` URL must be the full
`file:///C:/...` Windows form (a `/c/...` MSYS path → ERR_FILE_NOT_FOUND).
