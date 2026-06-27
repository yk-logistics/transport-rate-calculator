"""Data structures for fuel pump reconciliation. See spec
docs/superpowers/specs/2026-06-27-fuel-pump-reconcile-design.md."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class FuelBill:
    """One pump-report line (ground truth)."""
    date: date
    plate: str
    station: str
    ftype: str
    liter: float
    price: float
    amount: float


@dataclass
class SysFuel:
    """One FuelTxn row from the system."""
    date: date
    plate: str
    liter: float
    amount: float
    driver_id: Optional[int]
    driver_name: str
    pay_mode: str  # lcb_mao / lcb_trip / lcb_mixed / ""


@dataclass
class MatchResult:
    matched_pairs: int = 0
    matched_pump_baht: float = 0.0
    matched_sys_baht: float = 0.0
    pump_only: list[FuelBill] = field(default_factory=list)
    system_only: list[SysFuel] = field(default_factory=list)
    # full system list retained for driver-impact attribution (plate->owner)
    _all_sys: list[SysFuel] = field(default_factory=list)
