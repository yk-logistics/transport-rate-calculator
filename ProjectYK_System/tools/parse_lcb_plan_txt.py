# -*- coding: utf-8 -*-
"""
Parse LCB junior dispatch plan from LINE .txt (e.g. 21.05.26.txt).

Returns per-head assignments: plate, job, trips, liters_per_trip, need_liters, notes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Locked fuel formulas (L)
L_PER_TRIP: dict[str, float] = {
    "KAO": 50.0,
    "Conti": 50.0,
    "Haier": 100.0,
    "Lacation": 50.0,
    "KATOEN": 40.0,  # โอยืนยัน ~40 ล./เที่ยว
    "คลังวาฬ": 25.0,
    "ฟรีโซน": 25.0,  # NHL ตู้ฟรีโซน (มัก Con.[20])
    "เหรินเหอ": 70.0,  # WHALE / RENHER — โอยืนยัน ~70 ล./เที่ยว (ตู้ 40' หัว 10 ล้อ)
    "Oatside": 110.0,  # per day midpoint
}

SECTION_JOB_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"Oatsite|Oatside|DHLOatsite", re.I), "Oatside"),
    (re.compile(r"WHALE|เหรินเหอ|RERNHER|RENHER|เปิดRERNHER", re.I), "เหรินเหอ"),
    (re.compile(r"KAO", re.I), "KAO"),
    (re.compile(r"CONTINENTAL|KLND|Conti", re.I), "Conti"),
    (re.compile(r"HAIER|CJ\d", re.I), "Haier"),
    (re.compile(r"วาฬ|คลังวาฬ|NHL", re.I), "คลังวาฬ"),
    (re.compile(r"LOCATION|Lacation", re.I), "Lacation"),
]

RE_LOCATION_BLOCK = re.compile(
    r"Closing|Booking|บรรจุ\s*LOCATION|LOCATION\s*ชลบุรี", re.I
)

RE_HEAD = re.compile(r"หัว\s*(\d{2}-\d{4})", re.I)
RE_CON = re.compile(r"Con\.\s*\[\s*\d+\s*\]", re.I)
RE_BL = re.compile(r"^BL\.\s", re.I)
RE_BOL = re.compile(r"^Bol\.\s", re.I)
RE_PLATE_INLINE = re.compile(r"(\d{2}-\d{4})")
RE_REMARK_REPLACE = re.compile(
    r"(\d{2}-\d{4}).*?(?:ใช้ชั่วคราว|แทน|พัฒิยะ)", re.I
)
RE_REMARK_BROKEN = re.compile(r"(\d{2}-\d{4}).*?(?:ซ่อม|เสีย|ว่าง)", re.I)


@dataclass
class TruckAssignment:
    plate: str
    job: str
    trips: int
    liters_per_trip: float
    need_liters: float
    driver: str = ""
    section: str = ""
    customer_label: str = ""  # ชื่อลูกค้าจากหัวข้อ *** ในแผน LINE (โชว์บน HTML)
    notes: list[str] = field(default_factory=list)


@dataclass
class ParsedPlan:
    plan_date: str = ""
    header_stats: str = ""
    header_jobs: int | None = None
    header_running: int | None = None
    header_continuity: int | None = None
    header_repair: int | None = None
    assignments: list[TruckAssignment] = field(default_factory=list)
    replacements: dict[str, str] = field(default_factory=dict)  # broken -> substitute
    broken_plates: set[str] = field(default_factory=set)
    spare_plates: set[str] = field(default_factory=set)
    remarks: list[str] = field(default_factory=list)


def _parse_header_stats(line: str) -> dict[str, int | None]:
    """Parse e.g. งาน16วิ่ง16//ต่อเนื่อง1//ซ่อม2 from first LINE plan line."""
    out: dict[str, int | None] = {
        "header_jobs": None,
        "header_running": None,
        "header_continuity": None,
        "header_repair": None,
    }
    m = re.search(r"งาน(\d+)", line)
    if m:
        out["header_jobs"] = int(m.group(1))
    m = re.search(r"วิ่ง(\d+)", line)
    if m:
        out["header_running"] = int(m.group(1))
    m = re.search(r"ต่อเนื่อง(\d+)", line)
    if m:
        out["header_continuity"] = int(m.group(1))
    m = re.search(r"ซ่อม(\d+)", line)
    if m:
        out["header_repair"] = int(m.group(1))
    return out


def _detect_section_job(header: str) -> str | None:
    for pat, job in SECTION_JOB_HINTS:
        if pat.search(header):
            return job
    return None


def _is_whale_bol_line(ln: str) -> bool:
    """Bol. ที่เป็นตู้คลังปลาวาฬ — ไม่นับ Bol. นำหน้าบล็อกฟรีโซน (เช่น 53-449 Agent.)."""
    s = ln.strip()
    if not RE_BOL.search(s):
        return False
    if re.search(r"ฟรีโซน|free\s*zone", s, re.I):
        return False
    if re.search(r"^Bol\.\s+\S+\s+Agent\.\s*$", s, re.I):
        return False
    return True


def _subjob_customer_label(subjob: str) -> str:
    if subjob == "ฟรีโซน":
        return "ฟรีโซน"
    if subjob == "คลังวาฬ":
        return "คลังวาฬ"
    if subjob == "KATOEN":
        return "KATOEN"
    return subjob


def _customer_label_from_header(header: str, job: str) -> str:
    """ชื่อลูกค้า/กลุ่มงานสำหรับแสดงผล — จากหัวข้อบล็อก *** ในแผน LINE."""
    h = (header or "").strip()
    m = re.search(r"\[([^\]]+)\]", h)
    if m:
        raw = re.sub(r"\*.*$", "", m.group(1)).strip()
        raw = re.sub(r"\d+$", "", raw).strip()
        if raw:
            return raw
    if re.search(r"Oatsite|Oatside|DHLOatsite", h, re.I):
        return "Oatside"
    if re.search(r"WHALE|เหรินเหอ|RERNHER", h, re.I):
        return "เหรินเหอ"
    if re.search(r"วาฬ|NHL|คลัง", h, re.I):
        return "คลังวาฬ"
    if job and job != "Unknown":
        return job
    return h[:32] if h else job or "Unknown"


def _parse_remarks(block: str) -> tuple[dict[str, str], set[str], list[str]]:
    replacements: dict[str, str] = {}
    broken: set[str] = set()
    lines: list[str] = []
    text = block
    if "Remark" in text or "หมายเหตุ" in text:
        # 8681 broken + 8684 แทน — เฉพาะเมื่อ Remark ระบุชัด (ไม่ดึงจาก Spare)
        if (
            "8681" in text
            and "8684" in text
            and re.search(r"พัฒิยะ|ใช้ชั่วคราว|แทน", text, re.I)
        ):
            replacements["71-8681"] = "71-8684"
            broken.add("71-8681")
        if "1219" in text and "ซ่อม" in text:
            broken.add("72-1219")
        for line in text.splitlines():
            if "Remark" in line or "หมายเหตุ" in line or "ทะเบียน" in line:
                lines.append(line.strip())
    return replacements, broken, lines


def _apply_plate(plate: str, replacements: dict[str, str]) -> str:
    return replacements.get(plate, plate)


def parse_plan_text(text: str) -> ParsedPlan:
    lines = text.replace("\r\n", "\n").split("\n")
    plan = ParsedPlan()
    if lines:
        plan.header_stats = lines[0].strip()
        stats = _parse_header_stats(plan.header_stats)
        plan.header_jobs = stats["header_jobs"]
        plan.header_running = stats["header_running"]
        plan.header_continuity = stats["header_continuity"]
        plan.header_repair = stats["header_repair"]
        m = re.search(r"(\d{2}\.\d{2}\.\d{2})", lines[0])
        if m:
            plan.plan_date = m.group(1)

    # Remarks block (after last *** or explicit Remark section)
    remark_start = None
    for i, ln in enumerate(lines):
        if re.search(r"Remark|หมายเหตุ", ln, re.I):
            remark_start = i
            break
    if remark_start is not None:
        remark_lines: list[str] = []
        for ln in lines[remark_start:]:
            if ln.strip().startswith("***"):
                break
            if re.search(r"Spare\s*\[รองาน\]", ln, re.I):
                break
            remark_lines.append(ln)
        plan.replacements, plan.broken_plates, plan.remarks = _parse_remarks(
            "\n".join(remark_lines)
        )

    spare_start = None
    for i, ln in enumerate(lines):
        if re.search(r"Spare\s*\[รองาน\]", ln, re.I):
            spare_start = i
            break
    if spare_start is not None:
        for ln in lines[spare_start:]:
            hm = RE_HEAD.search(ln)
            if hm:
                plan.spare_plates.add(hm.group(1))

    # Split sections by *** (title is usually the line AFTER the stars row)
    sections: list[tuple[str, list[str]]] = []
    current_header = ""
    current_lines: list[str] = []
    pending_title = False

    def flush_section():
        nonlocal current_header, current_lines, pending_title
        if current_header or current_lines:
            sections.append((current_header, current_lines))
        current_header = ""
        current_lines = []
        pending_title = False

    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("***"):
            flush_section()
            title_on_same = stripped.strip("*").strip()
            pending_title = not title_on_same
            if title_on_same:
                current_header = title_on_same
            continue
        if pending_title and stripped:
            current_header = stripped
            pending_title = False
            continue
        if current_header or pending_title:
            current_lines.append(ln)
    flush_section()

    agg: dict[tuple[str, str], TruckAssignment] = {}

    for header, body in sections:
        if not header or re.search(r"Remark|Spare|ตู้วาย", header, re.I):
            continue
        section_job = _detect_section_job(header) or "Unknown"
        customer_label = _customer_label_from_header(header, section_job)
        if section_job == "Oatside":
            # Single truck section — count as 1 day job
            plate = driver = ""
            for ln in body:
                hm = RE_HEAD.search(ln)
                if hm:
                    plate = _apply_plate(hm.group(1), plan.replacements)
                if ln.strip().startswith("- นาย"):
                    driver = ln.strip().lstrip("- ").strip()
            if plate and plate not in plan.broken_plates:
                key = (plate, section_job)
                agg[key] = TruckAssignment(
                    plate=plate,
                    job=section_job,
                    trips=1,
                    liters_per_trip=L_PER_TRIP["Oatside"],
                    need_liters=L_PER_TRIP["Oatside"],
                    driver=driver,
                    section=header[:40],
                    customer_label=customer_label,
                    notes=["ประจำ Oatside — นอกชุด 16 เที่ยว"],
                )
            continue

        current_plate = ""
        current_driver = ""
        current_subjob = section_job
        pending_freezone = False
        trip_markers: list[str] = []
        location_mode = False

        def flush_plate():
            nonlocal current_plate, current_driver, trip_markers, location_mode, current_subjob
            if not current_plate or current_plate in plan.broken_plates:
                trip_markers = []
                return
            if location_mode:
                if re.search(r"KATOEN", header, re.I):
                    job = "KATOEN"
                    lpt = L_PER_TRIP["KATOEN"]
                    label = "KATOEN"
                else:
                    job = "Lacation"
                    lpt = L_PER_TRIP["Lacation"]
                    label = _subjob_customer_label(job)
            else:
                job = current_subjob
                lpt = L_PER_TRIP.get(job, 50.0)
                label = _subjob_customer_label(job)

            trips = len(trip_markers) if trip_markers else 0
            if trips == 0:
                trip_markers = []
                return

            key = (current_plate, job)
            need = trips * lpt
            note_extra: list[str] = []
            if current_plate in plan.replacements.values():
                for old, new in plan.replacements.items():
                    if new == current_plate:
                        note_extra.append(f"แทน {old}")
            if key in agg:
                prev = agg[key]
                prev.trips += trips
                prev.need_liters += need
                prev.notes.extend(note_extra)
            else:
                agg[key] = TruckAssignment(
                    plate=current_plate,
                    job=job,
                    trips=trips,
                    liters_per_trip=lpt,
                    need_liters=need,
                    driver=current_driver,
                    section=header[:40],
                    customer_label=label,
                    notes=note_extra,
                )
            trip_markers = []

        for ln in body:
            stripped = ln.strip()
            if RE_LOCATION_BLOCK.search(stripped):
                flush_plate()
                location_mode = True
            if re.search(r"^Job\.\s", stripped, re.I):
                flush_plate()
                current_plate = ""
                continue
            if section_job == "คลังวาฬ" and re.search(r"ฟรีโซน", stripped, re.I):
                flush_plate()
                pending_freezone = True
                continue
            if stripped.startswith("- นาย"):
                flush_plate()
                current_driver = stripped.lstrip("- ").strip()
                continue

            hm = RE_HEAD.search(ln)
            if hm:
                flush_plate()
                raw = hm.group(1)
                current_plate = _apply_plate(raw, plan.replacements)
                if pending_freezone:
                    current_subjob = "ฟรีโซน"
                    pending_freezone = False
                else:
                    current_subjob = section_job
                continue

            if not current_plate:
                continue

            if location_mode:
                if RE_CON.search(ln):
                    trip_markers.append(ln.strip()[:60])
            elif current_subjob == "คลังวาฬ":
                if _is_whale_bol_line(ln):
                    trip_markers.append(ln.strip()[:60])
            elif current_subjob == "ฟรีโซน":
                if RE_CON.search(ln):
                    trip_markers.append(ln.strip()[:60])
            elif RE_CON.search(ln):
                trip_markers.append(ln.strip()[:60])

        flush_plate()

    plan.assignments = sorted(
        agg.values(),
        key=lambda a: (
            [
                "Haier",
                "KAO",
                "Conti",
                "Lacation",
                "KATOEN",
                "คลังวาฬ",
                "ฟรีโซน",
                "เหรินเหอ",
                "Oatside",
                "Unknown",
            ].index(a.job)
            if a.job
            in [
                "Haier",
                "KAO",
                "Conti",
                "Lacation",
                "KATOEN",
                "คลังวาฬ",
                "ฟรีโซน",
                "เหรินเหอ",
                "Oatside",
                "Unknown",
            ]
            else 99,
            a.plate,
        ),
    )
    return plan


def plan_trip_stats(plan: ParsedPlan) -> dict[str, int]:
    """Container trips vs truck slots (Oatside separate from dispatch 16)."""
    dispatch = [a for a in plan.assignments if a.job != "Oatside"]
    oatside = [a for a in plan.assignments if a.job == "Oatside"]
    return {
        "container_trips_dispatch": sum(a.trips for a in dispatch),
        "container_trips_oatside": sum(a.trips for a in oatside),
        "container_trips_all": sum(a.trips for a in plan.assignments),
        "trucks_dispatch": len(dispatch),
        "trucks_with_oatside": len(plan.assignments),
    }


def parse_plan_file(path: Path | str) -> ParsedPlan:
    p = Path(path)
    return parse_plan_text(p.read_text(encoding="utf-8", errors="replace"))


def main() -> int:
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: parse_lcb_plan_txt.py <plan.txt>")
        return 1
    plan = parse_plan_file(sys.argv[1])
    stats = plan_trip_stats(plan)
    out = {
        "plan_date": plan.plan_date,
        "header_stats": plan.header_stats,
        "header_running": plan.header_running,
        "header_continuity": plan.header_continuity,
        "header_repair": plan.header_repair,
        "assignments": [
            {
                "plate": a.plate,
                "job": a.job,
                "trips": a.trips,
                "liters_per_trip": a.liters_per_trip,
                "need_liters": a.need_liters,
                "driver": a.driver,
                "customer_label": a.customer_label,
                "notes": a.notes,
            }
            for a in plan.assignments
        ],
        "replacements": plan.replacements,
        "broken": sorted(plan.broken_plates),
        "trip_total": stats["container_trips_dispatch"],
        "trucks_dispatch": stats["trucks_dispatch"],
        "trucks_with_oatside": stats["trucks_with_oatside"],
        "container_trips_all": stats["container_trips_all"],
        "trucks_match_header": (
            plan.header_running is not None
            and stats["trucks_with_oatside"] == plan.header_running
        ),
        "container_trips_vs_header": stats["container_trips_dispatch"]
        - (plan.header_running or 0),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
