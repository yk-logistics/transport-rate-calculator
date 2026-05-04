"""
Promote raw driver/plate references to Master (Employee / Vehicle).

Raw data accumulates in DailyJob / PettyCashTxn / FuelTxn via import.
This module:
  1. Surveys all unique raw names/plates
  2. Clusters them (e.g. "เนื้อ" and "นายเนื้อ ภาสดา" → same person)
  3. Infers defaults (home_site_code, pay_mode)
  4. Creates Employee/Vehicle records on demand
  5. Backfills driver_id/vehicle_id in existing raw-tagged rows
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from sqlmodel import Session, select

from models import DailyJob, Employee, FuelTxn, PettyCashTxn, Vehicle

# ---------- Name normalization ----------

_NAME_PREFIXES = ["นาย", "นาง", "น.ส.", "น.ส", "MR.", "MRS.", "MISS", "พี่", "พ่อบ้าน"]
# Tokens that indicate NOT a driver name (owner, manager, placeholders)
_SKIP_TOKENS = {"-", "รถจอด", "ขาด", "ลาป่วย", "ลากิจ", "ลา", "รับรถ", "(ว่าง)", "ว่าง", "นั่งฟรี"}


def normalize_name(raw: str) -> str:
    """Strip titles, spaces, punctuation; lowercase. Used as clustering key."""
    if not raw:
        return ""
    s = str(raw).strip()
    for pfx in _NAME_PREFIXES:
        if s.startswith(pfx):
            s = s[len(pfx):].strip()
    s = re.sub(r"[()\[\]\"']", "", s)
    s = re.sub(r"\s+", "", s)
    return s.lower()


def normalize_plate(raw: str) -> str:
    if not raw:
        return ""
    s = str(raw).strip().upper()
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", "", s)
    return s


def is_driver_like_name(raw: str) -> bool:
    if not raw:
        return False
    s = str(raw).strip()
    if s in _SKIP_TOKENS:
        return False
    n = normalize_name(s)
    if len(n) < 2:
        return False
    return True


# ---------- Survey ----------

@dataclass
class DriverCluster:
    """Group of raw name variants referring to the same person."""
    canonical_key: str         # normalized key used for grouping
    display_name: str          # best guess full_name for Employee
    nickname: str              # short form if known
    variants: list[str] = field(default_factory=list)
    site_counter: Counter = field(default_factory=Counter)
    source_counter: Counter = field(default_factory=Counter)
    plate_counter: Counter = field(default_factory=Counter)
    total: int = 0

    @property
    def home_site_code(self) -> str:
        for site, _ in self.site_counter.most_common():
            if site and site != "?":
                return site
        return ""

    @property
    def top_plate(self) -> str:
        if not self.plate_counter:
            return ""
        return self.plate_counter.most_common(1)[0][0]

    @property
    def is_confident(self) -> bool:
        """True if we're fairly sure this is a real driver."""
        if self.total < 3:
            return False
        if not self.home_site_code:
            return False
        # If ONLY seen in PettyCash → maybe a manager/owner; flag to review
        if set(self.source_counter) == {"PettyCash"}:
            return False
        return True

    @property
    def suggested_role(self) -> str:
        """Suggest role based on data pattern.

        - If only in PettyCash with non-driver-ish names (พ่อ, เมย์, admin) → office
        - If appears in Daily or Fuel → driver
        """
        if set(self.source_counter) == {"PettyCash"}:
            # Name-based hints for common non-driver roles
            low = (self.display_name or "").lower()
            if any(tok in low for tok in ("พ่อ", "แม่", "ออฟฟิส", "admin", "แอดมิน", "boss", "เจ้าของ")):
                return "owner" if "พ่อ" in low or "เจ้าของ" in low or "boss" in low else "office"
            return "office"
        return "driver"


@dataclass
class PlateCluster:
    normalized_plate: str
    display_plate: str
    site_counter: Counter = field(default_factory=Counter)
    source_counter: Counter = field(default_factory=Counter)
    total: int = 0

    @property
    def home_site_code(self) -> str:
        for site, _ in self.site_counter.most_common():
            if site and site != "?":
                return site
        return ""

    @property
    def is_confident(self) -> bool:
        return self.total >= 2 and bool(self.home_site_code)


_SITE_TOKENS_IN_NAME = re.compile(
    r"\s*(?:\(?\s*(?:big\s*c|bigc|ayu|อยุธยา|lcb|แหลม(?:ฉบัง)?)\s*\)?)\s*",
    re.IGNORECASE,
)


def _pick_canonical_display(variants: list[str]) -> tuple[str, str]:
    """Pick the best display (full) name and nickname from variant list.

    Rule:
      - Longest variant (minus title prefixes and inline site tags) = full_name
      - Shortest variant = nickname
    """
    if not variants:
        return "", ""
    stripped = []
    for v in variants:
        s = v.strip()
        for pfx in _NAME_PREFIXES:
            if s.startswith(pfx):
                s = s[len(pfx):].strip()
        # Remove inline site tags like "(BIG C)" or "อยุธยา" that the admin
        # sometimes adds to disambiguate when one person name repeats.
        cleaned = _SITE_TOKENS_IN_NAME.sub(" ", s).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        stripped.append(cleaned or s)
    # Use longest cleaned name as display
    longest = max(stripped, key=len)
    shortest = min(stripped, key=len)
    return longest, (shortest if shortest != longest else "")


def _cluster_drivers(items: list[tuple[str, str, str, str]]) -> list[DriverCluster]:
    """Cluster raw driver names by substring matching.

    items: list of (raw_name, site_code, source, plate_hint)
    """
    # Stage 1: group by exact normalized key
    by_key: dict[str, dict] = {}
    for raw, site, src, plate in items:
        if not is_driver_like_name(raw):
            continue
        k = normalize_name(raw)
        d = by_key.setdefault(k, {
            "variants": set(), "sites": Counter(),
            "sources": Counter(), "plates": Counter(),
        })
        d["variants"].add(raw.strip())
        d["sites"][site or "?"] += 1
        d["sources"][src] += 1
        if plate:
            d["plates"][plate.strip()] += 1

    # Stage 2: merge by substring using union-find so transitive merges work:
    # "สมัย" ⊂ "สมัย (big c)" AND "สมัย" ⊂ "สมัย อยุธยา" → all three end up as one cluster.
    keys_sorted = sorted(by_key.keys(), key=len)
    parent: dict[str, str] = {k: k for k in keys_sorted}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def try_union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        # Choose longer key as the root so display_name picking stays sensible.
        if len(ra) < len(rb):
            ra, rb = rb, ra
        # Site compatibility guard
        sites_a = {s for s, _ in by_key[ra]["sites"].most_common() if s != "?"}
        sites_b = {s for s, _ in by_key[rb]["sites"].most_common() if s != "?"}
        if sites_a and sites_b and not (sites_a & sites_b):
            return
        parent[rb] = ra
        by_key[ra]["variants"].update(by_key[rb]["variants"])
        by_key[ra]["sites"].update(by_key[rb]["sites"])
        by_key[ra]["sources"].update(by_key[rb]["sources"])
        by_key[ra]["plates"].update(by_key[rb]["plates"])

    for i, a in enumerate(keys_sorted):
        if len(a) < 3:
            continue
        for b in keys_sorted[i + 1:]:
            if a != b and a in b:
                try_union(a, b)

    clusters: list[DriverCluster] = []
    seen_roots: set[str] = set()
    for k in by_key.keys():
        root = find(k)
        if root in seen_roots:
            continue
        seen_roots.add(root)
        d = by_key[root]
        variants = sorted(d["variants"], key=len, reverse=True)
        full, short = _pick_canonical_display(variants)
        total = sum(d["sources"].values())
        clusters.append(DriverCluster(
            canonical_key=root,
            display_name=full,
            nickname=short,
            variants=variants,
            site_counter=d["sites"],
            source_counter=d["sources"],
            plate_counter=d["plates"],
            total=total,
        ))
    clusters.sort(key=lambda c: -c.total)
    return clusters


# ---------- Public API ----------

def survey_unpromoted_drivers(session: Session) -> list[DriverCluster]:
    """Find all raw driver names that haven't been linked to an Employee yet."""
    items: list[tuple[str, str, str, str]] = []

    for dj in session.exec(select(DailyJob).where(DailyJob.driver_id.is_(None))).all():
        if dj.driver_raw_name:
            items.append((dj.driver_raw_name, dj.site_code or "", "DailyJob", dj.plate_no_raw or ""))
    for p in session.exec(select(PettyCashTxn).where(PettyCashTxn.driver_id.is_(None))).all():
        if p.requester_raw:
            items.append((p.requester_raw, p.site_code or "", "PettyCash", p.linked_vehicle_plate_raw or ""))
    for f in session.exec(select(FuelTxn).where(FuelTxn.driver_id.is_(None))).all():
        if f.driver_raw_name:
            items.append((f.driver_raw_name, f.site_code or "", "Fuel", f.plate_no_raw or ""))

    clusters = _cluster_drivers(items)

    # Exclude any variant that already matches an existing Employee.full_name (case-insensitive)
    existing = session.exec(select(Employee)).all()
    existing_keys = {normalize_name(e.full_name) for e in existing}
    existing_keys |= {normalize_name(e.nickname) for e in existing if e.nickname}

    filtered = []
    for c in clusters:
        if c.canonical_key in existing_keys:
            continue
        # also skip if any variant normalizes to an existing key
        if any(normalize_name(v) in existing_keys for v in c.variants):
            continue
        filtered.append(c)
    return filtered


def survey_unpromoted_plates(session: Session) -> list[PlateCluster]:
    items: list[tuple[str, str, str]] = []
    for dj in session.exec(select(DailyJob).where(DailyJob.head_vehicle_id.is_(None))).all():
        if dj.plate_no_raw:
            items.append((dj.plate_no_raw, dj.site_code or "", "DailyJob"))
    for f in session.exec(select(FuelTxn).where(FuelTxn.vehicle_id.is_(None))).all():
        if f.plate_no_raw:
            items.append((f.plate_no_raw, f.site_code or "", "Fuel"))
    for p in session.exec(
        select(PettyCashTxn).where(PettyCashTxn.linked_vehicle_id.is_(None))
    ).all():
        if p.linked_vehicle_plate_raw:
            items.append((p.linked_vehicle_plate_raw, p.site_code or "", "PettyCash"))

    clusters: dict[str, PlateCluster] = {}
    for raw, site, src in items:
        n = normalize_plate(raw)
        if not n or n == "-":
            continue
        c = clusters.setdefault(n, PlateCluster(normalized_plate=n, display_plate=raw.strip()))
        c.site_counter[site or "?"] += 1
        c.source_counter[src] += 1
        c.total += 1

    existing = session.exec(select(Vehicle)).all()
    existing_keys = {normalize_plate(v.plate_no) for v in existing}

    return sorted(
        [c for k, c in clusters.items() if k not in existing_keys],
        key=lambda c: -c.total,
    )


def _default_pay_mode(site: str) -> str:
    return {
        "AYU": "ayu_trip",
        "BIGC": "bigc_monthly",
        "LCB": "lcb_monthly",
    }.get(site.upper(), "ayu_trip")


def promote_drivers(
    session: Session,
    selections: list[dict],
    code_gen,  # callable(session, Employee, prefix='E') -> str
) -> tuple[int, int]:
    """
    Create Employee rows and backfill driver_id in raw-tagged rows.

    selections: [
       {"variants": ["เนื้อ", "นายเนื้อ ภาสดา"], "full_name": "...", "nickname": "...",
        "home_site_code": "LCB", "pay_mode": "lcb_monthly", "role": "driver"},
    ]

    Returns (created_count, backfilled_rows).
    """
    created = 0
    filled = 0
    for sel in selections:
        variants = sel.get("variants") or []
        full_name = (sel.get("full_name") or "").strip()
        if not full_name or not variants:
            continue
        nickname = (sel.get("nickname") or "").strip()
        home = (sel.get("home_site_code") or "").strip() or "AYU"
        role = (sel.get("role") or "driver").strip()
        # For non-drivers, pay_mode defaults to "none" — they don't get payroll
        if role != "driver":
            pay_mode = sel.get("pay_mode") or "none"
        else:
            pay_mode = (sel.get("pay_mode") or _default_pay_mode(home))

        # Upsert: if an employee with matching normalized name already exists, skip create
        key = normalize_name(full_name)
        existing = session.exec(select(Employee)).all()
        match = next((e for e in existing if normalize_name(e.full_name) == key), None)
        if match is None:
            emp = Employee(
                code=code_gen(session, Employee, prefix="E"),
                full_name=full_name,
                nickname=nickname,
                home_site_code=home,
                role=role,
                pay_mode=pay_mode,
                status="active",
            )
            session.add(emp)
            session.flush()
            created += 1
        else:
            emp = match

        # Backfill — match on ANY variant (exact raw string match, case-insensitive normalized)
        variant_keys = {normalize_name(v) for v in variants}

        for dj in session.exec(select(DailyJob).where(DailyJob.driver_id.is_(None))).all():
            if dj.driver_raw_name and normalize_name(dj.driver_raw_name) in variant_keys:
                dj.driver_id = emp.id
                # Backfill site_code if empty
                if not dj.site_code:
                    dj.site_code = home
                filled += 1
        for p in session.exec(
            select(PettyCashTxn).where(PettyCashTxn.driver_id.is_(None))
        ).all():
            if p.requester_raw and normalize_name(p.requester_raw) in variant_keys:
                p.driver_id = emp.id
                if not p.site_code:
                    p.site_code = home
                filled += 1
        for f in session.exec(select(FuelTxn).where(FuelTxn.driver_id.is_(None))).all():
            if f.driver_raw_name and normalize_name(f.driver_raw_name) in variant_keys:
                f.driver_id = emp.id
                if not f.site_code:
                    f.site_code = home
                filled += 1
    session.commit()
    return created, filled


def promote_vehicles(
    session: Session,
    selections: list[dict],
    code_gen,  # not used for plate — plate IS the code
) -> tuple[int, int]:
    """
    selections: [
       {"plate_no": "71-0567", "home_site_code": "AYU", "truck_type": "6W"},
    ]
    """
    created = 0
    filled = 0
    for sel in selections:
        plate = normalize_plate(sel.get("plate_no", ""))
        if not plate or plate == "-":
            continue
        home = (sel.get("home_site_code") or "").strip()
        truck_type = (sel.get("truck_type") or "").strip()

        existing = session.exec(select(Vehicle)).all()
        match = next((v for v in existing if normalize_plate(v.plate_no) == plate), None)
        if match is None:
            veh = Vehicle(
                plate_no=plate,
                vehicle_kind="truck",
                truck_type=truck_type,
                home_site_code=home,
                status="active",
            )
            session.add(veh)
            session.flush()
            created += 1
        else:
            veh = match

        for dj in session.exec(
            select(DailyJob).where(DailyJob.head_vehicle_id.is_(None))
        ).all():
            if dj.plate_no_raw and normalize_plate(dj.plate_no_raw) == plate:
                dj.head_vehicle_id = veh.id
                filled += 1
        for f in session.exec(select(FuelTxn).where(FuelTxn.vehicle_id.is_(None))).all():
            if f.plate_no_raw and normalize_plate(f.plate_no_raw) == plate:
                f.vehicle_id = veh.id
                filled += 1
        for p in session.exec(
            select(PettyCashTxn).where(PettyCashTxn.linked_vehicle_id.is_(None))
        ).all():
            if p.linked_vehicle_plate_raw and normalize_plate(p.linked_vehicle_plate_raw) == plate:
                p.linked_vehicle_id = veh.id
                filled += 1
    session.commit()
    return created, filled
