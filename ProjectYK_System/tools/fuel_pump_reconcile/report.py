"""Render reconcile results to HTML + Markdown. Thai labels, English data keys.
See spec docs/superpowers/specs/2026-06-27-fuel-pump-reconcile-design.md."""
from __future__ import annotations

import os
from datetime import date

from matcher import driver_impact
from models import MatchResult


def _near_boundary(d: date, start: date, end: date, days: int = 2) -> bool:
    return (d - start).days <= days or (end - d).days <= days


def _summary(result: MatchResult, start: date, end: date) -> dict:
    pump_tot = result.matched_pump_baht + sum(b.amount for b in result.pump_only)
    sys_tot = result.matched_sys_baht + sum(s.amount for s in result.system_only)
    pb = sum(1 for b in result.pump_only if _near_boundary(b.date, start, end))
    sb = sum(1 for s in result.system_only if _near_boundary(s.date, start, end))
    return {
        "pump_total": pump_tot, "sys_total": sys_tot,
        "delta": pump_tot - sys_tot,
        "pct": (pump_tot - sys_tot) / sys_tot * 100 if sys_tot else 0.0,
        "matched": result.matched_pairs,
        "pump_only": len(result.pump_only), "system_only": len(result.system_only),
        "pump_only_near_boundary": pb, "system_only_near_boundary": sb,
    }


def render(result: MatchResult, cycle_tag: str, out_dir: str,
           start: date = None, end: date = None) -> tuple[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    if start is None:
        start = min([b.date for b in result.pump_only] +
                    [s.date for s in result.system_only] + [date.max])
    if end is None:
        end = max([b.date for b in result.pump_only] +
                  [s.date for s in result.system_only] + [date.min])
    s = _summary(result, start, end)
    impact = driver_impact(result)

    md = _render_md(result, s, impact, cycle_tag, start, end)
    html = _render_html(md)
    md_path = os.path.join(out_dir, f"fuel_reconcile_{cycle_tag}.md")
    html_path = os.path.join(out_dir, f"fuel_reconcile_{cycle_tag}.html")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    return html_path, md_path


def _b(d, start, end):
    return " (ขอบรอบ)" if _near_boundary(d, start, end) else ""


def _render_md(result, s, impact, cycle_tag, start, end) -> str:
    L = [f"# ตรวจน้ำมัน ปั๊ม ↔ ระบบ — รอบ {cycle_tag}", ""]
    L.append(f"ช่วง {start.isoformat()} ถึง {end.isoformat()}")
    L.append("")
    L.append("## สรุปยอด")
    L.append(f"- ปั๊ม (PDF) รวม: **{s['pump_total']:,.0f} ฿**")
    L.append(f"- ระบบ/ชีท รวม: **{s['sys_total']:,.0f} ฿**")
    L.append(f"- ส่วนต่าง: **{s['delta']:+,.0f} ฿** ({s['pct']:+.1f}%)")
    L.append(f"- จับคู่ได้: {s['matched']} บิล | ปั๊มเกิน: {s['pump_only']} "
             f"(ขอบรอบ {s['pump_only_near_boundary']}) | ระบบเกิน: {s['system_only']} "
             f"(ขอบรอบ {s['system_only_near_boundary']})")
    L.append("")

    # payroll-affecting section
    L.append("## 🔴 กระทบเงินเดือน (คนเหมา / mixed)")
    L.append("> หมายเหตุ: ตัวเลขต่อคนเป็น *ค่าประมาณ* — แบ่งน้ำมันด้วย 'เจ้าของทะเบียนหลัก' "
             "รถที่ใช้ร่วมกันอาจคลาด. 'สุทธิติดลบ' (ระบบเกินปั๊ม) มักเกิดเมื่อ PDF ปั๊มนี้ "
             "ไม่ครอบคลุมทุกสถานี (เช่นเติม ปตท.) — ไม่ใช่หักเกินเสมอไป. ใช้ตารางบิลด้านล่างยืนยันรายใบ.")
    L.append("")
    if not impact:
        L.append("ไม่มีคนเหมาที่ยอดน้ำมันไม่ตรง — ✅ ทุกคนกระทบเงิน = 0")
    else:
        L.append("| คน | โหมด | ปั๊มเกิน฿ | ระบบเกิน฿ | สุทธิ฿ | กระทบเงิน≈(×60%) |")
        L.append("|---|---|--:|--:|--:|--:|")
        for did, row in sorted(impact.items(), key=lambda kv: -abs(kv[1]["net_baht"])):
            flag = "✅" if abs(row["net_baht"]) < 1 else "⚠️"
            L.append(f"| {flag} {row['driver_name']} | {row['pay_mode']} | "
                     f"{row['pump_only_baht']:,.0f} | {row['sys_only_baht']:,.0f} | "
                     f"{row['net_baht']:+,.0f} | {row['money_impact']:,.0f} |")
    L.append("")

    L.append("## ปั๊มมี-ระบบไม่มี")
    L.append("| วันที่ | ทะเบียน | ฿ | |")
    L.append("|---|---|--:|---|")
    for b in sorted(result.pump_only, key=lambda x: (x.plate, x.date)):
        L.append(f"| {b.date.isoformat()} | {b.plate} | {b.amount:,.0f} |{_b(b.date, start, end)} |")
    L.append("")
    L.append("## ระบบมี-ปั๊มไม่มี")
    L.append("| วันที่ | ทะเบียน | คนขับ | ฿ | |")
    L.append("|---|---|---|--:|---|")
    for s2 in sorted(result.system_only, key=lambda x: (x.plate, x.date)):
        L.append(f"| {s2.date.isoformat()} | {s2.plate} | {s2.driver_name} | "
                 f"{s2.amount:,.0f} |{_b(s2.date, start, end)} |")
    L.append("")
    return "\n".join(L)


def _render_html(md: str) -> str:
    # minimal: wrap the markdown in <pre> so it's viewable without a md lib
    esc = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<title>Fuel Reconcile</title>"
            "<style>body{font-family:system-ui,sans-serif;margin:2rem;}"
            "pre{white-space:pre-wrap;font-size:14px;line-height:1.5;}</style>"
            f"</head><body><pre>{esc}</pre></body></html>")
