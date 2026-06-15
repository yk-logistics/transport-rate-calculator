# -*- coding: utf-8 -*-
"""
Parse Tekyong / เต็กย้ง pump credit PDF (รายงานการเติมน้ำมัน วายเค).

  python ProjectYK_System/tools/parse_pump_credit_pdf.py path/to/report.pdf
  python ... --out ProjectYK_System/reports/pump_credit_latest.json

Drop daily PDFs in ProjectYK_System/reports/pump_inbox/
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
PUMP_INBOX = ROOT / "reports" / "pump_inbox"
DEFAULT_OUT = ROOT / "reports" / "pump_credit_latest.json"
DEFAULT_CREDIT_LIMIT = 50_000.0

PLATE_RE = r"(?:\d{2}-\d{4}|บษ-\d{4}|บร-\d{4})"

ROW_FUEL = re.compile(
    rf"^(\d+)\s+(\d{{2}}\.\d{{2}}\.\d{{4}})\s+({PLATE_RE})\s+"
    r"(\S+)\s+Diesel\s+B7\s+"
    r"([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([-]?[\d.,]+)\s*$",
    re.UNICODE,
)

ROW_TOPUP = re.compile(
    r"^(\d+)\s+(\d{2}\.\d{2}\.\d{4})\s+(วายเค[^\d]+?)\s+"
    r"([\d.,]+)\s+([-]?[\d.,]+)\s*$",
    re.UNICODE,
)

OPENING_BALANCE_RE = re.compile(r"^([-]?[\d.,]+)\s*$")


def _num(s: str) -> float:
    return float(str(s).replace(",", "").strip())


def _parse_date_th(s: str) -> str:
    """DD.MM.YYYY -> YYYY-MM-DD"""
    d, m, y = s.split(".")
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def extract_pdf_text(path: Path) -> str:
    try:
        import pdfplumber
    except ImportError as exc:
        raise SystemExit(
            "ต้องติดตั้ง pdfplumber: pip install pdfplumber"
        ) from exc
    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            parts.append(t)
    return "\n".join(parts)


def parse_pump_credit_text(
    text: str,
    *,
    source_file: str = "",
    credit_limit_baht: float = DEFAULT_CREDIT_LIMIT,
) -> dict:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    lines = [ln for ln in lines if not ln.startswith("--") and " of " not in ln]

    transactions: list[dict] = []
    opening_balance: float | None = None
    saw_table = False

    for ln in lines:
        if "ยอดยกมา" in ln:
            continue
        m = ROW_FUEL.match(ln)
        if m:
            saw_table = True
            seq, dt, plate, station, liters, price_l, amount, balance = m.groups()
            transactions.append(
                {
                    "seq": int(seq),
                    "date_th": dt,
                    "date_iso": _parse_date_th(dt),
                    "kind": "fuel",
                    "plate": plate,
                    "station": station,
                    "liters": _num(liters),
                    "price_per_l": _num(price_l),
                    "amount_baht": _num(amount),
                    "balance_baht": _num(balance),
                }
            )
            continue
        m = ROW_TOPUP.match(ln)
        if m:
            saw_table = True
            seq, dt, label, amount, balance = m.groups()
            transactions.append(
                {
                    "seq": int(seq),
                    "date_th": dt,
                    "date_iso": _parse_date_th(dt),
                    "kind": "topup",
                    "plate": "",
                    "station": label.strip(),
                    "liters": 0.0,
                    "price_per_l": 0.0,
                    "amount_baht": _num(amount),
                    "balance_baht": _num(balance),
                }
            )
            continue
        if not saw_table and OPENING_BALANCE_RE.match(ln):
            opening_balance = _num(ln)

    if not transactions:
        return {
            "ok": False,
            "error": "ไม่พบรายการเติมน้ำมันใน PDF (รูปแบบไม่ตรง)",
            "source_file": source_file,
        }

    transactions.sort(key=lambda x: (x["date_iso"], x["seq"]))
    closing = transactions[-1]["balance_baht"]
    balances = [t["balance_baht"] for t in transactions]
    min_bal = min(balances)
    max_bal = max(balances)

    debt_baht = max(0.0, -closing)
    headroom = max(0.0, credit_limit_baht - debt_baht)
    at_risk = debt_baht >= credit_limit_baht * 0.85

    month_label = ""
    for ln in lines:
        if "ประจำเดือน" in ln or "พฤษภาคม" in ln or "เมษายน" in ln:
            month_label = ln[:80]
            break

    fuel_txns = [t for t in transactions if t["kind"] == "fuel"]
    topup_txns = [t for t in transactions if t["kind"] == "topup"]
    total_fuel_baht = sum(t["amount_baht"] for t in fuel_txns)
    total_topup_baht = sum(t["amount_baht"] for t in topup_txns)

    by_plate: dict[str, list[dict]] = {}
    for t in fuel_txns:
        by_plate.setdefault(t["plate"], []).append(t)

    return {
        "ok": True,
        "source_file": source_file,
        "parsed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "month_label": month_label,
        "opening_balance_baht": opening_balance,
        "closing_balance_baht": closing,
        "min_balance_baht": min_bal,
        "max_balance_baht": max_bal,
        "credit_limit_baht": credit_limit_baht,
        "debt_baht": round(debt_baht, 2),
        "headroom_before_limit_baht": round(headroom, 2),
        "at_risk": at_risk,
        "transaction_count": len(transactions),
        "fuel_fill_count": len(fuel_txns),
        "topup_count": len(topup_txns),
        "total_fuel_baht": round(total_fuel_baht, 2),
        "total_topup_baht": round(total_topup_baht, 2),
        "last_fuel_date_iso": fuel_txns[-1]["date_iso"] if fuel_txns else "",
        "last_topup": topup_txns[-1] if topup_txns else None,
        "transactions": transactions,
        "by_plate_last": {
            p: rows[-1] for p, rows in by_plate.items()
        },
    }


def parse_pump_credit_pdf(
    path: Path,
    *,
    credit_limit_baht: float = DEFAULT_CREDIT_LIMIT,
) -> dict:
    text = extract_pdf_text(path)
    return parse_pump_credit_text(
        text,
        source_file=path.name,
        credit_limit_baht=credit_limit_baht,
    )


def find_latest_pump_pdf() -> Path | None:
    dirs = [
        PUMP_INBOX,
        ROOT / "reports",
        Path.home() / "Downloads",
        Path.home() / "Desktop",
    ]
    seen: set[str] = set()
    candidates: list[Path] = []
    for folder in dirs:
        if not folder.is_dir():
            continue
        for p in folder.glob("*.pdf"):
            key = str(p.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            name = p.name.lower()
            if "เติมน้ำมัน" not in name and "fuel" not in name and "วายเค" not in name:
                if folder not in (PUMP_INBOX, ROOT / "reports"):
                    continue
            candidates.append(p)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def transactions_on_date(data: dict, date_iso: str) -> list[dict]:
    if not data.get("ok"):
        return []
    return [t for t in data["transactions"] if t["date_iso"] == date_iso]


def save_snapshot(data: dict, out_path: Path = DEFAULT_OUT) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def pump_summary_for_ui(
    data: dict,
    dispatch_plates: list[str] | None = None,
    *,
    max_yesterday_rows: int = 30,
) -> dict:
    """Subset for HTML embed (ไม่ใส่ transactions ทั้งก้อน)."""
    if not data.get("ok"):
        return data
    plates = set(dispatch_plates or [])
    ref_date = data.get("last_fuel_date_iso", "")
    yday: list[dict] = []
    for t in data.get("transactions", []):
        if t.get("kind") != "fuel":
            continue
        if ref_date and t.get("date_iso") != ref_date:
            continue
        if plates and t.get("plate") not in plates:
            continue
        yday.append(
            {
                "plate": t["plate"],
                "station": t.get("station", ""),
                "liters": t.get("liters", 0),
                "amount_baht": t.get("amount_baht", 0),
                "date_th": t.get("date_th", ""),
            }
        )
    topups = [t for t in data.get("transactions", []) if t.get("kind") == "topup"]
    return {
        "ok": True,
        "source_file": data.get("source_file", ""),
        "parsed_at": data.get("parsed_at", ""),
        "closing_balance_baht": data["closing_balance_baht"],
        "min_balance_baht": data["min_balance_baht"],
        "credit_limit_baht": data["credit_limit_baht"],
        "debt_baht": data["debt_baht"],
        "headroom_before_limit_baht": data["headroom_before_limit_baht"],
        "at_risk": data.get("at_risk", False),
        "last_fuel_date_iso": ref_date,
        "last_fuel_date_th": yday[0]["date_th"] if yday else "",
        "fuel_fill_count": data.get("fuel_fill_count", 0),
        "total_topup_baht": data.get("total_topup_baht", 0),
        "yesterday_fills": yday[:max_yesterday_rows],
        "recent_topups": [
            {
                "date_th": t.get("date_th"),
                "station": t.get("station"),
                "amount_baht": t.get("amount_baht"),
                "balance_baht": t.get("balance_baht"),
            }
            for t in topups[-5:]
        ],
    }


def load_snapshot(path: Path = DEFAULT_OUT) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Parse YK pump credit PDF (Tekyong)")
    ap.add_argument("pdf", nargs="?", type=Path, help="PDF path (default: newest in pump_inbox)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--credit-limit", type=float, default=DEFAULT_CREDIT_LIMIT)
    args = ap.parse_args()

    path = args.pdf
    if path is None:
        path = find_latest_pump_pdf()
        if path is None:
            print(f"ไม่พบ PDF ใน {PUMP_INBOX}")
            print("  วางไฟล์รายงานปั๊ม (ชื่อมี 'เติมน้ำมัน' หรือ 'วายเค')")
            return 1
        print(f"ใช้ PDF ล่าสุด: {path}")

    if not path.exists():
        print(f"ไม่พบไฟล์: {path}")
        return 1

    data = parse_pump_credit_pdf(path, credit_limit_baht=args.credit_limit)
    if not data.get("ok"):
        print(data.get("error", "parse failed"))
        return 1

    save_snapshot(data, args.out)
    print(f"OK: {args.out}")
    print(
        f"ยอดปิด: {data['closing_balance_baht']:,.2f} ฿ | "
        f"หนี้: {data['debt_baht']:,.0f} ฿ | "
        f"เหลือก่อนเพดาน {data['credit_limit_baht']:,.0f}: "
        f"{data['headroom_before_limit_baht']:,.0f} ฿"
    )
    print(
        f"รายการ: เติม {data['fuel_fill_count']} | โอนเติมวงเงิน {data['topup_count']} | "
        f"ต่ำสุดในรายงาน: {data['min_balance_baht']:,.2f} ฿"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
