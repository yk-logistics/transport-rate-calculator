"""Inject the trips-table export buttons (Print/PDF · Excel · PNG) into an already
generated Oatside trips.html WITHOUT rebuilding the report.

Why this exists: build_oatside_reports.py now emits these buttons, but a full rebuild
re-picks the *newest* GPS export (discover_gps_files) and would recompute the published
billing numbers. This patch adds only the export UI to existing HTML — money untouched.

Idempotent: skips a file that already has the buttons. Also copies the bundled
html2canvas.min.js (needed by the PNG button) next to each patched trips.html.

Usage:
    python ProjectYK_System/tools/patch_oatside_trips_export_buttons.py            # patch known locations
    python ProjectYK_System/tools/patch_oatside_trips_export_buttons.py <trips.html> [...]
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OATSIDE = REPO / "Oatside"
H2C_SRC = OATSIDE / "assets" / "html2canvas.min.js"

# Must match build_oatside_reports.py exactly.
CSS_SNIPPET = (
    ".export-bar{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 12px}"
    ".exp-btn{font:inherit;font-size:13px;font-weight:700;cursor:pointer;color:#0b57d0;"
    "background:#eef5ff;border:1px solid #b8cff4;border-radius:8px;padding:8px 13px}"
    ".exp-btn:hover{background:#dfeaff}"
)
BAR_SNIPPET = (
    "<div class='export-bar'>"
    "<button type='button' class='exp-btn' id='tripsAllTableExpPrint'>🖨️ พิมพ์ / PDF (เปิดหน้าตารางแยก)</button>"
    "<button type='button' class='exp-btn' id='tripsAllTableExpXls'>📊 Excel (ตามที่เห็น)</button>"
    "<button type='button' class='exp-btn' id='tripsAllTableExpPng'>🖼️ บันทึกรูป PNG</button>"
    "</div>\n"
)
BAR_ANCHOR = "<div class='table-scroll'><table id='tripsAllTable'>"

# Default targets: the published Pages clone + the local working copy (no rebuild needed).
DEFAULT_TARGETS = [
    REPO / "transport-rate-calculator-repo" / "reports" / "oatside-pg-2026" / "trips.html",
    REPO / "reports" / "oatside-pg-2026" / "trips.html",
]


def _export_js() -> str:
    sys.path.insert(0, str(OATSIDE))
    import build_oatside_reports as b  # noqa: E402

    return b._TABLE_EXPORT_JS


EXPORT_JS_SIG = "init('tripsAllTable',{title:'Oatside"


def _strip_old(html: str) -> bool:
    """Remove a previous injection so the patch can be re-applied with updated JS.
    Returns True if anything was stripped."""
    changed = False
    if CSS_SNIPPET in html:
        html_new = html.replace(CSS_SNIPPET, "")
        changed |= html_new != html
        html = html_new
    if BAR_SNIPPET in html:
        html_new = html.replace(BAR_SNIPPET, "")
        changed |= html_new != html
        html = html_new
    # remove the whole injected <script>…</script> that holds the export logic
    k = html.find(EXPORT_JS_SIG)
    if k != -1:
        start = html.rfind("<script>", 0, k)
        end = html.find("</script>", k)
        if start != -1 and end != -1:
            html = html[:start] + html[end + len("</script>"):]
            changed = True
    return html, changed


def patch_file(path: Path, export_js: str) -> str:
    if not path.exists():
        return "missing"
    html = path.read_text(encoding="utf-8")
    if BAR_ANCHOR not in html:
        return "skip (no #tripsAllTable anchor)"

    html, was_patched = _strip_old(html)
    # 1) CSS — before the first </style>
    i = html.index("</style>")
    html = html[:i] + CSS_SNIPPET + html[i:]
    # 2) toolbar — before the table
    html = html.replace(BAR_ANCHOR, BAR_SNIPPET + BAR_ANCHOR, 1)
    # 3) export script — before the closing </body>
    j = html.rindex("</body>")
    html = html[:j] + export_js + "\n" + html[j:]

    path.write_text(html, encoding="utf-8")
    _copy_h2c(path)
    return "re-patched (updated)" if was_patched else "patched"


def _copy_h2c(trips_path: Path) -> None:
    if H2C_SRC.exists():
        shutil.copy2(H2C_SRC, trips_path.parent / "html2canvas.min.js")


def main(argv: list[str]) -> None:
    targets = [Path(a) for a in argv] if argv else DEFAULT_TARGETS
    export_js = _export_js()
    for t in targets:
        print(f"{patch_file(t, export_js):<40}  {t}")


if __name__ == "__main__":
    main(sys.argv[1:])
