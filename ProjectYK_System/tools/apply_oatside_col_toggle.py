# -*- coding: utf-8 -*-
from pathlib import Path

P = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py")
t = P.read_text(encoding="utf-8")

OLD_CSS_END = (
    '"".trips-lead{color:#4b5b74;font-size:14px;margin:-2px 0 10px}"'
    "\n    )"
)
NEW_CSS_END = (
    '"".trips-lead{color:#4b5b74;font-size:14px;margin:-2px 0 10px}"'
    '""details.col-picker{margin:8px 0 14px;border:1px solid #c5d0e0;border-radius:10px;padding:0 14px 4px;background:#fff}"'
    '""details.col-picker summary{cursor:pointer;font-weight:700;padding:10px 0;font-size:13px;color:#12243b;list-style:none}"'
    '""details.col-picker summary::-webkit-details-marker{display:none}"'
    '"".col-picker-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:8px 16px;padding:4px 0 12px;font-size:13px}"'
    '"".col-picker-grid label{display:flex;gap:8px;align-items:flex-start;cursor:pointer;line-height:1.35}"'
    '"".col-picker-grid input{margin-top:3px;flex-shrink:0}"'
    "\n    )"
)
if OLD_CSS_END not in t:
    raise SystemExit("OLD_CSS_END not found")
t = t.replace(OLD_CSS_END, NEW_CSS_END, 1)

OLD_FILTER_END = (
    '    "})();</script>"\n'
    ")\n"
    "\n"
    "\n"
    "def html_fifty_surcharge_badge"
)
_NEW_BLOCK = (
    '    "})();</script>"\n'
    ")\n"
    "\n"
    "_COL_TOGGLE_JS = (\n"
    "    \"<script>(function(){\"\n"
    "    \"function boot(){\"\n"
    "    \"function init(tableId){\"\n"
    "    \"var tbl=document.getElementById(tableId);\"\n"
    "    \"if(!tbl)return;\"\n"
    "    \"var inner=document.getElementById(tableId+'ColInner');\"\n"
    "    \"var key='oatside_col_hidden:'+location.pathname+':'+tableId;\"\n"
    "    \"function loadH(){try{return JSON.parse(localStorage.getItem(key)||'[]')}catch(e){return[]}}\"\n"
    "    \"function saveH(a){localStorage.setItem(key,JSON.stringify(a))}\"\n"
    "    \"function applyH(hid){\"\n"
    "    \"var ths=tbl.querySelectorAll('thead tr th');var n=ths.length;\"\n"
    "    \"for(var c=0;c<n;c++){var hide=hid.indexOf(c)>=0;var disp=hide?'none':'';\"\n"
    "    \"var rows=tbl.querySelectorAll('tr');for(var r=0;r<rows.length;r++)\"\n"
    "    \"{var cell=rows[r].children[c];if(cell)cell.style.display=disp;}}\"\n"
    "    \"}\"\n"
    "    \"var hid=loadH();var ths=tbl.querySelectorAll('thead tr th');var n=ths.length;\"\n"
    "    \"if(inner){inner.innerHTML='';for(var i=0;i<n;i++)\"\n"
    "    \"{var lab=document.createElement('label');var cb=document.createElement('input');\"\n"
    "    \"cb.type='checkbox';cb.checked=hid.indexOf(i)<0;cb.setAttribute('data-ci',String(i));\"\n"
    "    \"var tx=(ths[i].textContent||'').trim()||('Col '+(i+1));lab.appendChild(cb);\"\n"
    "    \"lab.appendChild(document.createTextNode(' '+tx));\"\n"
    "    \"(function(ci){cb.addEventListener('change',function(ev){var h=loadH();var p=h.indexOf(ci);\"\n"
    "    \"if(ev.target.checked){if(p>=0)h.splice(p,1);}else{if(p<0)h.push(ci);}saveH(h);applyH(h);});})(i);\"\n"
    "    \"inner.appendChild(lab);}}applyH(hid);\"\n"
    "    \"var rb=document.getElementById(tableId+'ColReset');if(rb)rb.addEventListener('click',function(){\"\n"
    "    \"saveH([]);applyH([]);if(inner){var boxes=inner.querySelectorAll('input[type=checkbox]');\"\n"
    "    \"for(var j=0;j<boxes.length;j++)boxes[j].checked=true;}});}\"\n"
    "    \"init('tripsAllTable');init('plateTripsTable');}\"\n"
    "    \"if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();\"\n"
    "    \"})();</script>\"\n"
    ")\n"
    "\n"
    "\n"
    "def html_fifty_surcharge_badge"
)
if OLD_FILTER_END not in t:
    raise SystemExit("OLD_FILTER_END not found")
t = t.replace(OLD_FILTER_END, _NEW_BLOCK, 1)

OLD_TRIPS_FOOT = (
    "        + _TRIPS_FILTER_JS\n"
    '        + "\\n</body></html>"\n'
)
NEW_TRIPS_FOOT = (
    "        + _TRIPS_FILTER_JS\n"
    "        + _COL_TOGGLE_JS\n"
    '        + "\\n</body></html>"\n'
)
if OLD_TRIPS_FOOT not in t:
    raise SystemExit("OLD_TRIPS_FOOT not found")
t = t.replace(OLD_TRIPS_FOOT, NEW_TRIPS_FOOT, 1)

# ห้ามรวม placeholder ท้าย (เคาะ? กับไฟล์จริงอาจไม่เท่ากัน) — ยึด suffix ก่อนตาราง
OLD_TRIP_TABLE = (
    "autocomplete='off'></div>\n"
    "<div class='table-scroll'><table id='tripsAllTable'>"
)
NEW_TRIP_TABLE = (
    "autocomplete='off'></div>\n"
    "<details class='col-picker' id='tripsAllTableColPicker'><summary>แสดง / ซ่อนคอลัมน์ (เลือกได้เหมือน Excel)</summary>"
    "<div class='col-picker-grid' id='tripsAllTableColInner'></div>"
    "<p style='margin:0 0 10px'><button type='button' class='xlsx-dl' id='tripsAllTableColReset'>แสดงทุกคอลัมน์</button></p></details>\n"
    "<div class='table-scroll'><table id='tripsAllTable'>"
)
if OLD_TRIP_TABLE not in t:
    raise SystemExit("OLD_TRIP_TABLE not found")
t = t.replace(OLD_TRIP_TABLE, NEW_TRIP_TABLE, 1)

# Plate: ใช้ท้ายย่อหน้า freeze + หัวตาราง (ข้อความไทยในไฟล์จริง — อย่าใช้ ?????)
OLD_PLATE = (
    "เลื่อนในกรอบ)</p>\n"
    "<div class='table-scroll'><table><thead><tr>"
)
NEW_PLATE = (
    "เลื่อนในกรอบ)</p>\n"
    "<details class='col-picker' id='plateTripsTableColPicker'><summary>แสดง / ซ่อนคอลัมน์ (เลือกได้เหมือน Excel)</summary>"
    "<div class='col-picker-grid' id='plateTripsTableColInner'></div>"
    "<p style='margin:0 0 10px'><button type='button' class='xlsx-dl' id='plateTripsTableColReset'>แสดงทุกคอลัมน์</button></p></details>\n"
    "<div class='table-scroll'><table id='plateTripsTable'><thead><tr>"
)
if OLD_PLATE not in t:
    raise SystemExit("OLD_PLATE (freeze tail) not found")
t = t.replace(OLD_PLATE, NEW_PLATE, 1)

OLD_PG_END = (
    "{merged_plate_rows}</tbody></table></div></div>\n"
    "</body></html>\"\"\""
)
NEW_PG_END = (
    "{merged_plate_rows}</tbody></table></div></div>\n"
    '{_COL_TOGGLE_JS}\n'
    "</body></html>\"\"\""
)
if OLD_PG_END not in t:
    raise SystemExit("OLD_PG_END not found")
t = t.replace(OLD_PG_END, NEW_PG_END, 1)

P.write_text(t, encoding="utf-8")
print("OK:", P)
