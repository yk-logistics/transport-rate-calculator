# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "Oatside" / "build_oatside_reports.py"
s = P.read_text(encoding="utf-8")

if "class ManualExtraTrip" in s:
    print("build_oatside_reports.py already has ManualExtraTrip")
else:
    needle = (
        "        return (b - a).total_seconds() / 3600.0\n\n\n\n_DEFAULT_NO_WORK_RANGES:"
    )
    insert = (
        "        return (b - a).total_seconds() / 3600.0\n\n\n"
        "@dataclass(frozen=True)\n"
        "class ManualExtraTrip:\n"
        "    \"\"\"ลูกค้าตกลงเก็บเพิ่มแต่ไม่มีในไฟล์ GPS (เช่น P&G→Oatside).\"\"\"\n\n"
        "    dest_date: date\n"
        "    plate: str\n"
        "    amount_baht: int\n"
        "    note: str = \"\"\n\n\n\n"
        "_DEFAULT_NO_WORK_RANGES:"
    )
    if needle not in s:
        raise SystemExit("needle1 missing")
    s = s.replace(needle, insert, 1)

    s = s.replace(
        "    highlight_origin_wait_h: float\n    highlight_dest_wait_h: float\n",
        "    highlight_origin_wait_h: float\n    highlight_dest_wait_h: float\n"
        "    manual_extra_trips: tuple[ManualExtraTrip, ...]\n",
        1,
    )

    s = s.replace(
        "    highlight_origin_wait_h=8.0,\n    highlight_dest_wait_h=8.0,\n)\n\n\n_DEFAULT_CONFIG_JSON",
        "    highlight_origin_wait_h=8.0,\n    highlight_dest_wait_h=8.0,\n    manual_extra_trips=(),\n)\n\n\n_DEFAULT_CONFIG_JSON",
        1,
    )

    s = s.replace(
        '    "highlight_dest_wait_h": 8,\n',
        '    "highlight_dest_wait_h": 8,\n'
        '    "manual_extra_trips": [],\n'
        '    "_note_manual_extra_trips": "เที่ยวเพิ่มที่ไม่มีใน GPS — ตัวอย่าง: '
        '{\\"dest_date\\": \\"2026-04-22\\", \\"plate\\": \\"72-1217\\", '
        '\\"amount_baht\\": 7500, \\"note\\": \\"P&G->Oatside\\"}",\n',
        1,
    )

    ins = (
        "    manual_list: list[ManualExtraTrip] = []\n"
        "    raw_mx = raw.get(\"manual_extra_trips\")\n"
        "    if isinstance(raw_mx, list):\n"
        "        for e in raw_mx:\n"
        "            if not isinstance(e, dict):\n"
        "                continue\n"
        "            ds = str(e.get(\"dest_date\", \"\")).strip()[:10]\n"
        "            pl = str(e.get(\"plate\", \"\")).strip()\n"
        "            try:\n"
        "                amt = int(e.get(\"amount_baht\", 0) or 0)\n"
        "            except (TypeError, ValueError):\n"
        "                amt = 0\n"
        "            note = str(e.get(\"note\", \"\")).strip()\n"
        "            if len(ds) < 10 or not pl or amt <= 0:\n"
        "                continue\n"
        "            try:\n"
        "                dd = datetime.strptime(ds, \"%Y-%m-%d\").date()\n"
        "            except ValueError:\n"
        "                continue\n"
        "            manual_list.append(ManualExtraTrip(dest_date=dd, plate=pl, amount_baht=amt, note=note))\n\n"
    )
    ret = "    return OatsideConfig(\n"
    if ret not in s:
        raise SystemExit("return OatsideConfig anchor missing")
    s = s.replace(ret, ins + ret, 1)

    s = s.replace(
        "        highlight_dest_wait_h=float(\n"
        "            raw.get(\"highlight_dest_wait_h\", _DEFAULT_CONFIG.highlight_dest_wait_h)\n"
        "        ),\n"
        "    )\n",
        "        highlight_dest_wait_h=float(\n"
        "            raw.get(\"highlight_dest_wait_h\", _DEFAULT_CONFIG.highlight_dest_wait_h)\n"
        "        ),\n"
        "        manual_extra_trips=tuple(manual_list),\n"
        "    )\n",
        1,
    )

    pre = "def _tr_prepend_day_band(html: str, day: date) -> str:\n"
    helpers = (
        "def sum_manual_extra_baht(cfg: OatsideConfig) -> int:\n"
        "    return sum(m.amount_baht for m in cfg.manual_extra_trips)\n\n\n"
        "def merge_manual_extra_into_pday(pday_rows: list[dict], cfg: OatsideConfig) -> None:\n"
        "    for m in cfg.manual_extra_trips:\n"
        "        found = False\n"
        "        for r in pday_rows:\n"
        "            if str(r[\"plate\"]) == m.plate and r[\"dest_date\"] == m.dest_date:\n"
        "                r[\"base_line_baht\"] = int(r[\"base_line_baht\"]) + m.amount_baht\n"
        "                r[\"customer_day_baht\"] = int(r[\"customer_day_baht\"]) + m.amount_baht\n"
        "                r[\"matched_trips\"] = int(r[\"matched_trips\"]) + 1\n"
        "                tag = esc(m.note) if m.note else \"เที่ยวเพิ่ม (ไม่มีใน GPS)\"\n"
        "                badge = (\n"
        "                    f\"<span class='badge manual-extra' title='{tag}'>\"\n"
        "                    f\"เที่ยวเพิ่ม +{m.amount_baht:,}฿</span>\"\n"
        "                )\n"
        "                prev = (r.get(\"fifty_badge_html\") or \"\").strip()\n"
        "                r[\"fifty_badge_html\"] = (prev + \" \" + badge).strip() if prev else badge\n"
        "                found = True\n"
        "                break\n"
        "        if not found:\n"
        "            rate = trip_rate_baht(m.dest_date, cfg)\n"
        "            tag = esc(m.note) if m.note else \"เที่ยวเพิ่ม (ไม่มีใน GPS)\"\n"
        "            badge = (\n"
        "                f\"<span class='badge manual-extra' title='{tag}'>\"\n"
        "                f\"เที่ยวเพิ่ม +{m.amount_baht:,}฿</span>\"\n"
        "            )\n"
        "            pday_rows.append(\n"
        "                {\n"
        "                    \"dest_date\": m.dest_date,\n"
        "                    \"plate\": m.plate,\n"
        "                    \"site\": site_for_plate(m.plate),\n"
        "                    \"matched_trips\": 1,\n"
        "                    \"trip_rate_baht\": rate,\n"
        "                    \"base_line_baht\": m.amount_baht,\n"
        "                    \"fifty_pct_baht\": 0,\n"
        "                    \"fifty_badge_html\": badge,\n"
        "                    \"customer_day_baht\": m.amount_baht,\n"
        "                }\n"
        "            )\n"
        "    pday_rows.sort(key=lambda r: (r[\"dest_date\"], str(r[\"plate\"])))\n\n\n"
        "def merge_manual_extra_into_audit(audit_rows: list[dict], cfg: OatsideConfig) -> None:\n"
        "    for m in cfg.manual_extra_trips:\n"
        "        hit = False\n"
        "        for r in audit_rows:\n"
        "            if str(r[\"plate\"]) != m.plate or r.get(\"dest_date\") != m.dest_date:\n"
        "                continue\n"
        "            r[\"base_line_baht\"] = int(r[\"base_line_baht\"]) + m.amount_baht\n"
        "            r[\"customer_day_baht\"] = int(r[\"customer_day_baht\"]) + m.amount_baht\n"
        "            r[\"matched_trips\"] = int(r[\"matched_trips\"]) + 1\n"
        "            extra = (\n"
        "                f\" | เที่ยวเพิ่ม (ไม่มีใน GPS): {m.note} (+{m.amount_baht:,}฿)\"\n"
        "                if m.note\n"
        "                else f\" | เที่ยวเพิ่ม (ไม่มีใน GPS) +{m.amount_baht:,}฿\"\n"
        "            )\n"
        "            r[\"billing_note\"] = str(r.get(\"billing_note\", \"\")) + extra\n"
        "            hit = True\n"
        "            break\n"
        "        if hit:\n"
        "            continue\n"
        "        rate = trip_rate_baht(m.dest_date, cfg)\n"
        "        note = (\n"
        "            f\"เที่ยวเพิ่ม (ไม่มีใน GPS): {m.note} (+{m.amount_baht:,}฿)\"\n"
        "            if m.note\n"
        "            else f\"เที่ยวเพิ่ม (ไม่มีใน GPS) +{m.amount_baht:,}฿\"\n"
        "        )\n"
        "        audit_rows.append(\n"
        "            {\n"
        "                \"origin_day\": m.dest_date,\n"
        "                \"dest_date\": m.dest_date,\n"
        "                \"plate\": m.plate,\n"
        "                \"site\": site_for_plate(m.plate),\n"
        "                \"matched_trips\": 1,\n"
        "                \"trip_rate_baht\": rate,\n"
        "                \"base_line_baht\": m.amount_baht,\n"
        "                \"fifty_pct_baht\": 0,\n"
        "                \"customer_day_baht\": m.amount_baht,\n"
        "                \"billing_note\": note,\n"
        "            }\n"
        "        )\n"
        "    audit_rows.sort(key=lambda r: (r.get(\"origin_day\", r[\"dest_date\"]), str(r[\"plate\"])))\n\n\n"
        "def apply_manual_extra_to_cpd(cpd_rows: list[dict], cfg: OatsideConfig) -> None:\n"
        "    by_d = {r[\"dest_date\"]: r for r in cpd_rows}\n"
        "    for m in cfg.manual_extra_trips:\n"
        "        if m.dest_date in by_d:\n"
        "            by_d[m.dest_date][\"matched_trips\"] = int(by_d[m.dest_date][\"matched_trips\"]) + 1\n"
        "        else:\n"
        "            cpd_rows.append(\n"
        "                {\"dest_date\": m.dest_date, \"matched_trips\": 1, \"active_trucks\": 1}\n"
        "            )\n"
        "            by_d[m.dest_date] = cpd_rows[-1]\n"
        "    cpd_rows.sort(key=lambda r: r[\"dest_date\"])\n\n\n"
    )
    if pre not in s:
        raise SystemExit("_tr_prepend missing")
    s = s.replace(pre, helpers + pre, 1)

    old_um = '        "tr.um td{color:#5a3b00}"\n'
    s = s.replace(
        old_um,
        old_um + '        ".manual-extra{background:#ede7f6;color:#4a148c;font-weight:600}"\n',
        1,
    )

    old_audit_block = (
        "    if cfg.use_origin_day_fifty:\n"
        "        audit_rows = origin_day_audit_rows(trips, fifty_rows, overrides, cfg)\n"
        "    elif cfg.use_origin_24h_fifty:\n"
        "        audit_rows = audit_log_rows(trips, fifty_rows, overrides, cfg)\n"
        "    else:\n"
        "        audit_rows = audit_log_rows(trips, fifty_rows, overrides, cfg)\n"
        "    base_baht = base_trips_revenue_baht(trips, cfg)\n"
    )
    new_audit_block = (
        "    if cfg.use_origin_day_fifty:\n"
        "        audit_rows = origin_day_audit_rows(trips, fifty_rows, overrides, cfg)\n"
        "    elif cfg.use_origin_24h_fifty:\n"
        "        audit_rows = audit_log_rows(trips, fifty_rows, overrides, cfg)\n"
        "    else:\n"
        "        audit_rows = audit_log_rows(trips, fifty_rows, overrides, cfg)\n"
        "    merge_manual_extra_into_audit(audit_rows, cfg)\n"
        "    base_baht = base_trips_revenue_baht(trips, cfg) + sum_manual_extra_baht(cfg)\n"
    )
    if old_audit_block not in s:
        raise SystemExit("main audit block missing")
    s = s.replace(old_audit_block, new_audit_block, 1)

    s = s.replace(
        "    pday_rows = plate_dest_day_rows(trips, fifty_rows, cfg, nw_rows=nw_rows)\n",
        "    pday_rows = plate_dest_day_rows(trips, fifty_rows, cfg, nw_rows=nw_rows)\n"
        "    merge_manual_extra_into_pday(pday_rows, cfg)\n",
        1,
    )

    s = s.replace(
        "    customer_grand_baht = int(base_baht) + int(grand_extra)\n\n    xlsx_out",
        "    customer_grand_baht = int(base_baht) + int(grand_extra)\n\n"
        "    cpd_rows = customer_trips_per_day_rows(trips)\n"
        "    apply_manual_extra_to_cpd(cpd_rows, cfg)\n\n    xlsx_out",
        1,
    )

    old_ex_sig = (
        "    phantom_rows: list[dict],\n"
        "    hint_rows: list[dict],\n"
        ") -> None:\n"
        "    base_baht = base_trips_revenue_baht(trips, cfg)\n"
        "    pday = plate_dest_day_rows(trips, fifty_rows, cfg, nw_rows=no_work_rows)\n"
    )
    new_ex_sig = (
        "    phantom_rows: list[dict],\n"
        "    hint_rows: list[dict],\n"
        "    pday_rows: list[dict],\n"
        "    cpd_rows: list[dict],\n"
        ") -> None:\n"
        "    base_baht = base_trips_revenue_baht(trips, cfg) + sum_manual_extra_baht(cfg)\n"
        "    pday = pday_rows\n"
    )
    if old_ex_sig not in s:
        raise SystemExit("write_excel sig not found")
    s = s.replace(old_ex_sig, new_ex_sig, 1)

    s = s.replace(
        '    info.append(["Base_trips_revenue_baht", base_baht])\n',
        '    info.append(["Base_trips_revenue_baht", base_baht])\n'
        '    info.append(["Manual_extra_trips_baht", sum_manual_extra_baht(cfg)])\n',
        1,
    )

    old_cs = (
        '    cs.append(["A", "ค่าเที่ยวปกติ (นับ 1 เที่ยว = 1 เรทตามวันที่ Dest_In)", base_baht])\n'
    )
    new_cs = (
        "    mx = sum_manual_extra_baht(cfg)\n"
        '    cs.append(["A", "ค่าเที่ยวปกติ (GPS matched + เที่ยวเพิ่มจาก config)", base_baht])\n'
        "    if mx:\n"
        '        cs.append(["A2", "ในนั้น: เที่ยวเพิ่ม (manual_extra_trips ไม่มีใน GPS)", mx])\n'
    )
    if old_cs not in s:
        raise SystemExit("Customer_Summary A missing")
    s = s.replace(old_cs, new_cs, 1)

    s = s.replace(
        "    cpd_rows = customer_trips_per_day_rows(trips)\n    cpd = wb.create_sheet(\"Customer_Trips_Per_Day\")\n",
        "    cpd = wb.create_sheet(\"Customer_Trips_Per_Day\")\n",
        1,
    )

    s = s.replace(
        "    nw = wb.create_sheet(\"NoWork_Outbound_50pct\")\n",
        "    mx = wb.create_sheet(\"Manual_Extra_Trips\")\n"
        '    mx.append(["Dest_In_date", "Plate", "Amount_baht", "Note"])\n'
        "    for m in cfg.manual_extra_trips:\n"
        "        mx.append([m.dest_date, m.plate, m.amount_baht, m.note])\n"
        "    nw = wb.create_sheet(\"NoWork_Outbound_50pct\")\n",
        1,
    )

    old_wh = (
        "    nw_total_baht: int,\n"
        "    cfg: OatsideConfig,\n"
        ") -> None:\n"
    )
    new_wh = (
        "    nw_total_baht: int,\n"
        "    cfg: OatsideConfig,\n"
        "    cpd_rows: list[dict],\n"
        ") -> None:\n"
    )
    if old_wh not in s:
        raise SystemExit("write_html sig not found")
    s = s.replace(old_wh, new_wh, 1)

    s = s.replace(
        "        for r in customer_trips_per_day_rows(trips)\n",
        "        for r in cpd_rows\n",
        1,
    )

    old_we_call = (
        "        hint_rows,\n"
        "    )\n\n"
        "    report_dir = _root()"
    )
    new_we_call = (
        "        hint_rows,\n"
        "        pday_rows,\n"
        "        cpd_rows,\n"
        "    )\n\n"
        "    report_dir = _root()"
    )
    if old_we_call not in s:
        raise SystemExit("write_excel call tail not found")
    s = s.replace(old_we_call, new_we_call, 1)

    old_wh_call = (
        "        int(nw_total),\n"
        "        cfg,\n"
        "    )\n\n"
        "    print(f\"Config:"
    )
    new_wh_call = (
        "        int(nw_total),\n"
        "        cfg,\n"
        "        cpd_rows,\n"
        "    )\n\n"
        "    print(f\"Config:"
    )
    if old_wh_call not in s:
        raise SystemExit("write_html call tail not found")
    s = s.replace(old_wh_call, new_wh_call, 1)

    P.write_text(s, encoding="utf-8")
    print("patched", P)

# --- Merge 72-1217 into oatside_config.json if key absent ---
cfg_path = ROOT / "Oatside" / "oatside_config.json"
if cfg_path.is_file():
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print("skip oatside_config.json:", e)
    else:
        if isinstance(data, dict) and "manual_extra_trips" not in data:
            data["manual_extra_trips"] = [
                {
                    "dest_date": "2026-04-22",
                    "plate": "72-1217",
                    "amount_baht": 7500,
                    "note": "P&G → Oatside (เที่ยวเพิ่ม — ไม่มีใน GPS)",
                }
            ]
            data["_note_manual_extra_trips"] = (
                "เที่ยวที่ลูกค้าตกลงเก็บแต่ไม่มีในไฟล์ GPS — ลบ array ได้ถ้าไม่ใช้"
            )
            cfg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print("updated", cfg_path)
        else:
            print("oatside_config.json already has manual_extra_trips or unreadable")
else:
    print("no oatside_config.json — defaults in build script only")
