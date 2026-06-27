"""Reconcile pump FuelBills against system SysFuel rows.

Match by (plate, amount) allowing date drift; pump dates the fill-day while the
system dates the work-day, so a 1-2 day shift is normal. See spec
docs/superpowers/specs/2026-06-27-fuel-pump-reconcile-design.md."""
from __future__ import annotations

from datetime import date

from models import FuelBill, MatchResult, SysFuel


def reconcile(
    bills: list[FuelBill],
    sysfuel: list[SysFuel],
    start: date,
    end: date,
    drift_days: int = 3,
    amount_tol: float = 1.0,
) -> MatchResult:
    r = MatchResult()
    used = [False] * len(sysfuel)
    for b in bills:
        best = -1
        best_dist = drift_days + 1
        for i, s in enumerate(sysfuel):
            if used[i] or s.plate != b.plate or abs(s.amount - b.amount) > amount_tol:
                continue
            dist = abs((s.date - b.date).days)
            if dist < best_dist:
                best_dist = dist
                best = i
        if best >= 0:
            used[best] = True
            r.matched_pairs += 1
            r.matched_pump_baht += b.amount
            r.matched_sys_baht += sysfuel[best].amount
        else:
            r.pump_only.append(b)
    r.system_only = [sysfuel[i] for i in range(len(sysfuel)) if not used[i]]
    r._all_sys = list(sysfuel)
    return r


def driver_impact(result: MatchResult, mao_share: float = 0.60) -> dict:
    """Per-driver unmatched totals for เหมา/mixed drivers only (the ones whose
    fuel is deducted from pay). Returns {driver_id: {...}}.

    system_only attributes by its own driver_id. pump_only (FuelBills, no driver)
    attributes via plate->dominant-driver learned from the full sysfuel set, so a
    pump bill on a เหมา driver's plate counts toward that driver.
    """
    all_sys = getattr(result, "_all_sys", [])
    # plate -> (driver_id, pay_mode, name) using the driver who fuels that plate most
    plate_liters: dict[str, dict[int, float]] = {}
    plate_info: dict[int, tuple] = {}
    for s in all_sys:
        if s.driver_id is None:
            continue
        plate_liters.setdefault(s.plate, {})
        plate_liters[s.plate][s.driver_id] = plate_liters[s.plate].get(s.driver_id, 0.0) + s.liter
        plate_info[s.driver_id] = (s.pay_mode, s.driver_name)
    plate_owner = {p: max(d.items(), key=lambda x: x[1])[0] for p, d in plate_liters.items()}

    impact: dict[int, dict] = {}

    def _row(did):
        mode, name = plate_info.get(did, ("", ""))
        return impact.setdefault(did, {
            "driver_name": name, "pay_mode": mode,
            "pump_only_baht": 0.0, "sys_only_baht": 0.0,
        })

    def _is_mao(mode):
        return mode in ("lcb_mao", "lcb_mixed")

    for s in result.system_only:
        if s.driver_id is not None and _is_mao(s.pay_mode):
            _row(s.driver_id)["sys_only_baht"] += s.amount
    for b in result.pump_only:
        did = plate_owner.get(b.plate)
        if did is not None and _is_mao(plate_info.get(did, ("",))[0]):
            _row(did)["pump_only_baht"] += b.amount

    for row in impact.values():
        net = row["pump_only_baht"] - row["sys_only_baht"]
        row["net_baht"] = net
        row["money_impact"] = abs(net) * mao_share
    return impact
