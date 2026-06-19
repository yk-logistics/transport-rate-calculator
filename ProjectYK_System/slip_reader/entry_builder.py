from __future__ import annotations
import json
from .engine import SlipReadout
from .name_match import best_name_match


def _category(memo: str) -> str:
    m = memo or ""
    if "เบิก" in m:
        return "driver_advance"
    if "m flow" in m.lower() or "mflow" in m.lower() or "ทาง" in m:
        return "toll"
    if "ล้าง" in m:
        return "loading"
    return "other"  # คืนตู้/รับตู้/เข้าท่า ฯลฯ


def _ddmmyy_to_iso(day: str) -> str:
    # "16.06.26" -> "2026-06-16"
    dd, mm, yy = day.split(".")
    return f"20{yy}-{mm}-{dd}"


def build_entry(readout: SlipReadout, *, day: str, plan: dict,
                slip_line_message_id: str, slip_media_path: str):
    """Assemble the /api/petty/ingest payload from a slip readout + day plan.

    Returns None if this isn't a usable slip (not a slip, or no amount) — the
    money rule: never post an amount we didn't read from a slip.
    """
    if not readout.is_slip or readout.amount is None:
        return None
    name = (readout.recipient_name or "").strip()
    first = name.split()[0] if name.split() else name
    # Fuzzy-match the OCR'd name to the day's plan roster (correctly-spelled
    # driver names). On a hit, use the plan's canonical spelling — corrects OCR
    # typos like วิไรจน์→วิโรจน์. This is what drives who gets paid, so accuracy matters.
    roster = [k for k in (plan or {}) if k]
    matched = best_name_match(name, roster)
    plan_entry = None
    if matched:
        first = matched  # canonical spelling from the plan
        lst = plan.get(matched)
        plan_entry = lst[0] if lst else None
    memo = readout.memo or ""
    if plan_entry:
        extra = " ".join(x for x in (plan_entry.get("agent", ""),
                                     plan_entry.get("return_yard", "")) if x).strip()
        if extra:
            memo = f"{memo} / {extra}".strip(" /")
    return {
        "slip_line_message_id": slip_line_message_id,
        "site_code": "LCB",
        "txn_date": _ddmmyy_to_iso(day),
        "amount": float(readout.amount),
        "direction": readout.direction or "out",
        "category": _category(readout.memo),
        "requester_raw": first,
        "memo": memo,
        "slip_media_path": slip_media_path,
        "slip_ref_code": readout.ref_code or "",
        "parsed_confidence": 0.9 if plan_entry else 0.6,
        "parsed_payload_json": json.dumps(readout.__dict__, ensure_ascii=False),
    }
