# -*- coding: utf-8 -*-
"""Add manual_return_trips (ค่าขนส่งขากลับ flat) to Oatside/build_oatside_reports.py."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "Oatside" / "build_oatside_reports.py"


def main() -> None:
    s = P.read_text(encoding="utf-8")
    if "manual_return_trips" in s and "def sum_manual_return_baht" in s:
        print("already patched")
        return

    s = s.replace(
        "    manual_extra_trips: tuple[ManualExtraTrip, ...]\n\n@dataclass\nclass CustomerIdleWindow",
        "    manual_extra_trips: tuple[ManualExtraTrip, ...]\n"
        "    manual_return_trips: tuple[ManualExtraTrip, ...]\n\n"
        "@dataclass\nclass CustomerIdleWindow",
        1,
    )

    s = s.replace(
        "    manual_extra_trips=(),\n)\n\n\n_DEFAULT_CONFIG_JSON = {",
        "    manual_extra_trips=(),\n    manual_return_trips=(),\n)\n\n\n_DEFAULT_CONFIG_JSON = {",
        1,
    )

    s = s.replace(
        '    "manual_extra_trips": [],\n'
        '    "_note_manual_extra_trips": "เที่ยวเพิ่มที่ไม่มีใน GPS — ตัวอย่าง: '
        '{\\"dest_date\\": \\"2026-04-22\\", \\"plate\\": \\"72-1217\\", '
        '\\"amount_baht\\": 7500, \\"note\\": \\"P&G→Oatside\\"}",\n'
        '    "_note_long_dest_wait_midnight":',
        '    "manual_extra_trips": [],\n'
        '    "manual_return_trips": [],\n'
        '    "_note_manual_extra_trips": "เที่ยวเพิ่มที่ไม่มีใน GPS — ตัวอย่าง: '
        '{\\"dest_date\\": \\"2026-04-22\\", \\"plate\\": \\"72-1217\\", '
        '\\"amount_baht\\": 7500, \\"note\\": \\"P&G→Oatside\\"}",\n'
        '    "_note_manual_return_trips": "ค่าขนส่งขากลับ (flat) แยกจากเที่ยว GPS — '
        'ไม่เพิ่มจำนวน matched; รูปแบบเดียวกับ manual_extra_trips",\n'
        '    "_note_long_dest_wait_midnight":',
        1,
    )

    a0 = (
        "            manual_list.append(ManualExtraTrip(dest_date=dd, plate=pl, amount_baht=amt, note=note))\n\n"
        "    return OatsideConfig(\n"
    )
    if a0 not in s:
        raise SystemExit("load_oatside_config manual_list anchor missing")
    s = s.replace(
        a0,
        "            manual_list.append(ManualExtraTrip(dest_date=dd, plate=pl, amount_baht=amt, note=note))\n\n"
        "    return_list: list[ManualExtraTrip] = []\n"
        "    raw_rt = raw.get(\"manual_return_trips\")\n"
        "    if isinstance(raw_rt, list):\n"
        "        for e in raw_rt:\n"
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
        "            return_list.append(ManualExtraTrip(dest_date=dd, plate=pl, amount_baht=amt, note=note))\n\n"
        "    return OatsideConfig(\n",
        1,
    )

    s = s.replace(
        "        manual_extra_trips=tuple(manual_list),\n    )\n",
        "        manual_extra_trips=tuple(manual_list),\n        manual_return_trips=tuple(return_list),\n    )\n",
        1,
    )

    helpers = (
        "\n\ndef sum_manual_return_baht(cfg: OatsideConfig) -> int:\n"
        "    return sum(m.amount_baht for m in cfg.manual_return_trips)\n\n\n"
        "def merge_manual_return_into_pday(pday_rows: list[dict], cfg: OatsideConfig) -> None:\n"
        "    for m in cfg.manual_return_trips:\n"
        "        found = False\n"
        "        for r in pday_rows:\n"
        "            if str(r[\"plate\"]) == m.plate and r[\"dest_date\"] == m.dest_date:\n"
        "                prev = int(r.get(\"return_trip_baht\", 0) or 0)\n"
        "                r[\"return_trip_baht\"] = prev + int(m.amount_baht)\n"
        "                r[\"customer_day_baht\"] = int(r[\"customer_day_baht\"]) + int(m.amount_baht)\n"
        "                tag = esc(m.note) if m.note else \"ค่าขนส่งขากลับ (manual)\"\n"
        "                badge = (\n"
        "                    f\"<span class='badge return-trip' title='{tag}'>\"\n"
        "                    f\"ขากลับ +{m.amount_baht:,}฿</span>\"\n"
        "                )\n"
        "                prev_b = (r.get(\"fifty_badge_html\") or \"\").strip()\n"
        "                r[\"fifty_badge_html\"] = (prev_b + \" \" + badge).strip() if prev_b else badge\n"
        "                found = True\n"
        "                break\n"
        "        if not found:\n"
        "            rate = trip_rate_baht(m.dest_date, cfg)\n"
        "            tag = esc(m.note) if m.note else \"ค่าขนส่งขากลับ (manual)\"\n"
        "            badge = (\n"
        "                f\"<span class='badge return-trip' title='{tag}'>\"\n"
        "                f\"ขากลับ +{m.amount_baht:,}฿</span>\"\n"
        "            )\n"
        "            pday_rows.append(\n"
        "                {\n"
        "                    \"dest_date\": m.dest_date,\n"
        "                    \"plate\": m.plate,\n"
        "                    \"site\": site_for_plate(m.plate),\n"
        "                    \"matched_trips\": 0,\n"
        "                    \"trip_rate_baht\": rate,\n"
        "                    \"base_line_baht\": 0,\n"
        "                    \"fifty_pct_baht\": 0,\n"
        "                    \"fifty_badge_html\": badge,\n"
        "                    \"return_trip_baht\": int(m.amount_baht),\n"
        "                    \"customer_day_baht\": int(m.amount_baht),\n"
        "                }\n"
        "            )\n"
        "    pday_rows.sort(key=lambda r: (r[\"dest_date\"], str(r[\"plate\"])))\n\n\n"
        "def merge_manual_return_into_audit(audit_rows: list[dict], cfg: OatsideConfig) -> None:\n"
        "    for m in cfg.manual_return_trips:\n"
        "        hit = False\n"
        "        for r in audit_rows:\n"
        "            if str(r[\"plate\"]) != m.plate or r.get(\"dest_date\") != m.dest_date:\n"
        "                continue\n"
        "            prev = int(r.get(\"return_trip_baht\", 0) or 0)\n"
        "            r[\"return_trip_baht\"] = prev + int(m.amount_baht)\n"
        "            r[\"customer_day_baht\"] = int(r[\"customer_day_baht\"]) + int(m.amount_baht)\n"
        "            extra = (\n"
        "                f\" | ขากลับ (manual): {m.note} (+{m.amount_baht:,}฿)\"\n"
        "                if m.note\n"
        "                else f\" | ขากลับ (manual) +{m.amount_baht:,}฿\"\n"
        "            )\n"
        "            r[\"billing_note\"] = str(r.get(\"billing_note\", \"\")) + extra\n"
        "            hit = True\n"
        "            break\n"
        "        if hit:\n"
        "            continue\n"
        "        rate = trip_rate_baht(m.dest_date, cfg)\n"
        "        note = (\n"
        "            f\"ขากลับ (manual): {m.note} (+{m.amount_baht:,}฿)\"\n"
        "            if m.note\n"
        "            else f\"ขากลับ (manual) +{m.amount_baht:,}฿\"\n"
        "        )\n"
        "        audit_rows.append(\n"
        "            {\n"
        "                \"origin_day\": m.dest_date,\n"
        "                \"dest_date\": m.dest_date,\n"
        "                \"plate\": m.plate,\n"
        "                \"site\": site_for_plate(m.plate),\n"
        "                \"matched_trips\": 0,\n"
        "                \"trip_rate_baht\": rate,\n"
        "                \"base_line_baht\": 0,\n"
        "                \"fifty_pct_baht\": 0,\n"
        "                \"return_trip_baht\": int(m.amount_baht),\n"
        "                \"customer_day_baht\": int(m.amount_baht),\n"
        "                \"billing_note\": note,\n"
        "            }\n"
        "        )\n"
        "    audit_rows.sort(key=lambda r: (r.get(\"origin_day\", r[\"dest_date\"]), str(r[\"plate\"])))\n"
    )

    pre = "def _tr_prepend_day_band(html: str, day: date) -> str:\n"
    if pre not in s:
        raise SystemExit("_tr_prepend_day_band anchor missing")
    s = s.replace(pre, helpers + "\n" + pre, 1)

    s = s.replace(
        "\"fifty_badge_html\": badge,\n                \"customer_day_baht\": base_line + sur,\n",
        "\"fifty_badge_html\": badge,\n                \"return_trip_baht\": 0,\n                \"customer_day_baht\": base_line + sur,\n",
        2,
    )

    s = s.replace(
        "    fifty_by_lists: dict[tuple[str, date], list[dict]],\n    cfg: OatsideConfig,\n) -> str:\n",
        "    fifty_by_lists: dict[tuple[str, date], list[dict]],\n    cfg: OatsideConfig,\n    return_baht: int = 0,\n) -> str:\n",
        1,
    )
    s = s.replace(
        "    \"\"\"HTML <td>.x4 after wait columns: base rate, downtime+50, downtime+100, blank(no-work)+50.\"\"\"\n",
        "    \"\"\"HTML <td>.x5 after wait columns: base, downtime+50, downtime+100, blank+50, return flat.\"\"\"\n",
        1,
    )
    s = s.replace(
        "        + money_td(dw100)\n        + money_td(nw_amt)\n    )\n",
        "        + money_td(dw100)\n        + money_td(nw_amt)\n        + money_td(return_baht)\n    )\n",
        1,
    )

    s = s.replace(
        "        f\"<td>{dash}</td><td>{dash}</td><td>{dash}</td><td>{dash}</td></tr>\"\n",
        "        f\"<td>{dash}</td><td>{dash}</td><td>{dash}</td><td>{dash}</td><td>{dash}</td></tr>\"\n",
        1,
    )

    s = s.replace(
        "    merge_manual_extra_into_pday(pday_rows, cfg)\n",
        "    merge_manual_extra_into_pday(pday_rows, cfg)\n    merge_manual_return_into_pday(pday_rows, cfg)\n",
        1,
    )
    s = s.replace(
        "    merge_manual_extra_into_audit(audit_rows, cfg)\n",
        "    merge_manual_extra_into_audit(audit_rows, cfg)\n    merge_manual_return_into_audit(audit_rows, cfg)\n",
        1,
    )
    s = s.replace(
        "    customer_grand_baht = int(base_baht) + int(grand_extra)\n",
        "    customer_grand_baht = int(base_baht) + int(grand_extra) + int(sum_manual_return_baht(cfg))\n",
        1,
    )

    s = s.replace(
        "    info.append([\"Manual_extra_trips_baht\", sum_manual_extra_baht(cfg)])\n",
        "    info.append([\"Manual_extra_trips_baht\", sum_manual_extra_baht(cfg)])\n"
        "    info.append([\"Manual_return_trips_baht\", sum_manual_return_baht(cfg)])\n",
        1,
    )

    s = s.replace(
        "    if mx:\n"
        "        cs.append([\"A2\", \"ในนั้น: เที่ยวเพิ่ม (manual_extra_trips ไม่มีใน GPS)\", mx])\n",
        "    if mx:\n"
        "        cs.append([\"A2\", \"ในนั้น: เที่ยวเพิ่ม (manual_extra_trips ไม่มีใน GPS)\", mx])\n"
        "    mr = sum_manual_return_baht(cfg)\n"
        "    if mr:\n"
        "        cs.append(\n"
        "            [\n"
        "                \"R\",\n"
        "                \"ค่าขนส่งขากลับ (manual_return_trips — ไม่เพิ่มจำนวน matched)\",\n"
        "                mr,\n"
        "            ]\n"
        "        )\n",
        1,
    )

    s = s.replace(
        "    tot_lbl = (\n        \"Grand (A+B+C+D)\"\n        if cfg.charge_min_trip_shortfall\n        else \"Grand (A+C+D)\"\n    )\n",
        "    tot_lbl = (\n        \"Grand (A+B+C+D)\"\n        if cfg.charge_min_trip_shortfall\n        else (\"Grand (A+C+D+R)\" if sum_manual_return_baht(cfg) else \"Grand (A+C+D)\")\n    )\n",
        1,
    )

    s = s.replace(
        "        \"Dest_In_date\", \"Plate\", \"Site\", \"Matched_trips\",\n"
        "        \"Trip_rate_baht\", \"Base_line_baht\", \"Fifty_pct_baht\", \"Customer_day_baht\",\n",
        "        \"Dest_In_date\", \"Plate\", \"Site\", \"Matched_trips\",\n"
        "        \"Trip_rate_baht\", \"Base_line_baht\", \"Fifty_pct_baht\", \"Return_trip_baht\", \"Customer_day_baht\",\n",
        1,
    )
    s = s.replace(
        "            r[\"dest_date\"], r[\"plate\"], r[\"site\"], r[\"matched_trips\"],\n"
        "            r[\"trip_rate_baht\"], r[\"base_line_baht\"], r[\"fifty_pct_baht\"], r[\"customer_day_baht\"],\n",
        "            r[\"dest_date\"], r[\"plate\"], r[\"site\"], r[\"matched_trips\"],\n"
        "            r[\"trip_rate_baht\"], r[\"base_line_baht\"], r[\"fifty_pct_baht\"],\n"
        "            int(r.get(\"return_trip_baht\", 0) or 0),\n"
        "            r[\"customer_day_baht\"],\n",
        1,
    )

    s = s.replace(
        "        \"เที่ยว\", \"เรท(฿)\", \"ค่าเที่ยว(฿)\",\n"
        "        f\"+{cfg.one_trip_surcharge_pct:.0f}%(฿)\", \"รวมวันนี้(฿)\",\n",
        "        \"เที่ยว\", \"เรท(฿)\", \"ค่าเที่ยว(฿)\",\n"
        "        f\"+{cfg.one_trip_surcharge_pct:.0f}%(฿)\", \"ขากลับ(฿)\", \"รวมวันนี้(฿)\",\n",
        1,
    )
    s = s.replace(
        "            r[\"matched_trips\"], r[\"trip_rate_baht\"], r[\"base_line_baht\"],\n"
        "            r[\"fifty_pct_baht\"], r[\"customer_day_baht\"],\n",
        "            r[\"matched_trips\"], r[\"trip_rate_baht\"], r[\"base_line_baht\"],\n"
        "            r[\"fifty_pct_baht\"], int(r.get(\"return_trip_baht\", 0) or 0), r[\"customer_day_baht\"],\n",
        1,
    )

    s = s.replace(
        "        \"Travel_Flag\", \"Billable_Trip\", \"Nw_outbound50_baht\",\n",
        "        \"Travel_Flag\", \"Billable_Trip\", \"Nw_outbound50_baht\", \"Return_manual_baht\",\n",
        1,
    )

    trip_loop_anchor = (
        "    firsts = first_matched_trip_by_plate_dest(trips)\n"
        "    first_no_work = first_no_work_trip_by_plate_recovery_day(trips, cfg)\n"
        "    for t in sorted(trips, key=lambda x: (x.dest_date, x.plate, x.d_in)):\n"
    )
    if trip_loop_anchor not in s:
        raise SystemExit("Trip_Detail loop anchor missing")
    s = s.replace(
        trip_loop_anchor,
        "    firsts = first_matched_trip_by_plate_dest(trips)\n"
        "    first_no_work = first_no_work_trip_by_plate_recovery_day(trips, cfg)\n"
        "    ret_by_pd: dict[tuple[str, date], int] = {}\n"
        "    for m in cfg.manual_return_trips:\n"
        "        k = (str(m.plate), m.dest_date)\n"
        "        ret_by_pd[k] = int(ret_by_pd.get(k, 0)) + int(m.amount_baht)\n"
        "    for t in sorted(trips, key=lambda x: (x.dest_date, x.plate, x.d_in)):\n",
        1,
    )

    s = s.replace(
        "            t.travel_flag, 1, trip_no_work_outbound_baht(t, first_no_work, cfg),\n        ])\n",
        "            t.travel_flag, 1, trip_no_work_outbound_baht(t, first_no_work, cfg),\n"
        "            (\n"
        "                int(ret_by_pd.get((str(t.plate), t.dest_date), 0))\n"
        "                if firsts.get((t.plate, t.dest_date)) is not None\n"
        "                and id(firsts.get((t.plate, t.dest_date))) == id(t)\n"
        "                else 0\n"
        "            ),\n        ])\n",
        1,
    )

    s = s.replace(
        "    for m in cfg.manual_extra_trips:\n        mx.append([m.dest_date, m.plate, m.amount_baht, m.note])\n    nw = wb.create_sheet(\"NoWork_Outbound_50pct\")\n",
        "    for m in cfg.manual_extra_trips:\n        mx.append([m.dest_date, m.plate, m.amount_baht, m.note])\n"
        "    mr = wb.create_sheet(\"Manual_Return_Trips\")\n"
        "    mr.append([\"Dest_In_date\", \"Plate\", \"Amount_baht\", \"Note\"])\n"
        "    for m in cfg.manual_return_trips:\n        mr.append([m.dest_date, m.plate, m.amount_baht, m.note])\n"
        "    nw = wb.create_sheet(\"NoWork_Outbound_50pct\")\n",
        1,
    )

    s = s.replace(
        "    firsts = first_matched_trip_by_plate_dest(trips)\n    first_no_work = first_no_work_trip_by_plate_recovery_day(trips, cfg)\n    um_section_html = \"\".join(\n",
        "    firsts = first_matched_trip_by_plate_dest(trips)\n    first_no_work = first_no_work_trip_by_plate_recovery_day(trips, cfg)\n"
        "    ret_by_pd: dict[tuple[str, date], int] = {}\n"
        "    for m in cfg.manual_return_trips:\n"
        "        k = (str(m.plate), m.dest_date)\n"
        "        ret_by_pd[k] = int(ret_by_pd.get(k, 0)) + int(m.amount_baht)\n"
        "    um_section_html = \"\".join(\n",
        1,
    )

    trip_money_old = (
        "        money = trip_row_pricing_cells(\n"
        "            t, firsts=firsts, first_no_work=first_no_work, fifty_by_lists=fifty_by_lists, cfg=cfg\n"
        "        )\n"
    )
    trip_money_new = (
        "        ft0 = firsts.get((t.plate, t.dest_date))\n"
        "        ret_amt = (\n"
        "            int(ret_by_pd.get((str(t.plate), t.dest_date), 0))\n"
        "            if ft0 is not None and id(ft0) == id(t)\n"
        "            else 0\n"
        "        )\n"
        "        money = trip_row_pricing_cells(\n"
        "            t,\n"
        "            firsts=firsts,\n"
        "            first_no_work=first_no_work,\n"
        "            fifty_by_lists=fifty_by_lists,\n"
        "            cfg=cfg,\n"
        "            return_baht=ret_amt,\n"
        "        )\n"
    )
    if s.count(trip_money_old) != 2:
        raise SystemExit(f"expected trip_money_old x2, got {s.count(trip_money_old)}")
    s = s.replace(trip_money_old, trip_money_new, 2)

    s = s.replace(
        ".manual-extra{background:#ede7f6;color:#4a148c;font-weight:600}",
        ".manual-extra{background:#ede7f6;color:#4a148c;font-weight:600}"
        ".return-trip{background:#e8f5e9;color:#1b5e20;font-weight:600}",
        1,
    )

    s = s.replace(
        "<th>ตีเปล่า+50%(฿)</th></tr></thead><tbody>\n{merged_all_rows}",
        "<th>ตีเปล่า+50%(฿)</th><th>ขากลับ(฿)</th></tr></thead><tbody>\n{merged_all_rows}",
        1,
    )

    plate_head_old = (
        "<th>Dest Wait</th><th>ค่าขนส่ง(฿)</th><th>เสียเวลา+50%(฿)</th><th>เสียเวลา+100%(฿)</th><th>ตีเปล่า+50%(฿)</th></tr></thead><tbody>{merged_plate_rows}"
    )
    plate_head_new = (
        "<th>Dest Wait</th><th>ค่าขนส่ง(฿)</th><th>เสียเวลา+50%(฿)</th><th>เสียเวลา+100%(฿)</th><th>ตีเปล่า+50%(฿)</th><th>ขากลับ(฿)</th></tr></thead><tbody>{merged_plate_rows}"
    )
    if plate_head_old not in s:
        raise SystemExit("plate page trip table header missing")
    s = s.replace(plate_head_old, plate_head_new, 1)

    s = s.replace(
        "<b>ค่าเงิน:</b> ค่าขนส่ง = เรทวัน Dest_In ของเที่ยวนั้น · <b>เสียเวลา+50%/+100%</b> = ยอดรวมส่วนเพิ่ม fifty ของ (ทะเบียน×วัน Dest_In) แสดงที่แถวแรกของวันนั้น — <b>ไม่ได้คิดจากชั่วโมงในช่อง Dest Wait โดยตรง</b> (สีส้ม = แค่เตือนว่ารอปลายทางเกินเกณฑ์)</p>",
        "<b>ค่าเงิน:</b> ค่าขนส่ง = เรทวัน Dest_In ของเที่ยวนั้น · <b>เสียเวลา+50%/+100%</b> = ยอดรวมส่วนเพิ่ม fifty ของ (ทะเบียน×วัน Dest_In) แสดงที่แถวแรกของวันนั้น — <b>ไม่ได้คิดจากชั่วโมงในช่อง Dest Wait โดยตรง</b> (สีส้ม = แค่เตือนว่ารอปลายทางเกินเกณฑ์)"
        " · <b>ขากลับ(฿)</b> = ยอดจาก <code>manual_return_trips</code> แสดงที่แถวแรกของวันนั้น (ไม่เพิ่มจำนวนเที่ยว matched)</p>",
        1,
    )

    s = s.replace(
        "<th>ค่าเที่ยว(฿)</th><th>ส่วนเพิ่ม (฿)</th><th>รวมวัน(฿)</th></tr></thead><tbody>\n",
        "<th>ค่าเที่ยว(฿)</th><th>ส่วนเพิ่ม (฿)</th><th>ขากลับ(฿)</th><th>รวมวัน(฿)</th></tr></thead><tbody>\n",
        1,
    )

    s = s.replace(
        "<td class='money'>{r['customer_day_baht']:,}</td></tr>\" for r in pday_rows) or \"<tr><td colspan=8>ไม่มีข้อมูล</td></tr>\"}",
        "<td class='money'>{int(r.get('return_trip_baht',0) or 0):,}</td><td class='money'>{r['customer_day_baht']:,}</td></tr>\" for r in pday_rows) or \"<tr><td colspan=9>ไม่มีข้อมูล</td></tr>\"}",
        1,
    )

    s = s.replace(
        "<th>ส่วนเพิ่ม (฿)</th><th>รวม(฿)</th><th>เหตุผล</th></tr></thead><tbody>\n{audit_html or \"<tr><td colspan=9>ไม่มีข้อมูล</td></tr>\"}",
        "<th>ส่วนเพิ่ม (฿)</th><th>ขากลับ(฿)</th><th>รวม(฿)</th><th>เหตุผล</th></tr></thead><tbody>\n{audit_html or \"<tr><td colspan=10>ไม่มีข้อมูล</td></tr>\"}",
        1,
    )

    s = s.replace(
        "        f\"<td class='{'money' if r['fifty_pct_baht'] else ''}'>{r['fifty_pct_baht']:,}</td>\"\n"
        "        f\"<td class='money'>{r['customer_day_baht']:,}</td>\"\n",
        "        f\"<td class='{'money' if r['fifty_pct_baht'] else ''}'>{r['fifty_pct_baht']:,}</td>\"\n"
        "        f\"<td class='money'>{int(r.get('return_trip_baht',0) or 0):,}</td>\"\n"
        "        f\"<td class='money'>{r['customer_day_baht']:,}</td>\"\n",
        1,
    )

    P.write_text(s, encoding="utf-8")
    print("patched", P)


if __name__ == "__main__":
    main()
