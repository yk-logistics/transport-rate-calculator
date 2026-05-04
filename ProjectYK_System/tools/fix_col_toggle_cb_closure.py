from pathlib import Path

p = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py")
t = p.read_text(encoding="utf-8")
old = (
    '    "(function(ci){cb.addEventListener(\'change\',function(ev){var h=loadH();var p=h.indexOf(ci);"\n'
    '    "if(ev.target.checked){if(p>=0)h.splice(p,1);}else{if(p<0)h.push(ci);}saveH(h);applyH(h);});})(i);"\n'
)
new = (
    '    "(function(ci,cbx){cbx.addEventListener(\'change\',function(ev){var h=loadH();var p=h.indexOf(ci);"\n'
    '    "if(ev.target.checked){if(p>=0)h.splice(p,1);}else{if(p<0)h.push(ci);}saveH(h);applyH(h);});})(i,cb);"\n'
)
if old not in t:
    raise SystemExit("closure pattern not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("ok")
