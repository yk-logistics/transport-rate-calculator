from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


# .../ProjectYK_System/TransportRateCalculator/tools/this.py → repo root = parents[3]
ROOT_DIR = Path(__file__).resolve().parents[3]
TRC_DIR = Path(__file__).resolve().parents[1]
SALARY_DIR = ROOT_DIR / "data" / "Salary"
OUTPUT_DIR = TRC_DIR / "reports" / "petty-cash-online"

SITE_WORKBOOKS = {
    "AYU": SALARY_DIR / "AYU" / "สดย่อยวังน้อย.xlsx",
    "BigC": SALARY_DIR / "BigC" / "สดย่อยวังน้อย.xlsx",
    "LCB": SALARY_DIR / "LCB" / "สดย่อยวังน้อย.xlsx",
}

IGNORED_SHEETS = {"FORM (6)"}
FINANCE_KEYWORDS = ("เงินกู้", "ไฟแนนซ์", "ดอก", "ผ่อน", "ค่างวด", "leasing")
ADVANCE_KEYWORDS = ("เงินเบิก", "เบิก", "สำรอง")
CONTAINER_KEYWORDS = ("รับตู้", "คืนตู้")


def _find_header_row(raw_df: pd.DataFrame) -> int | None:
    for idx in range(min(30, len(raw_df))):
        row = [str(v).strip() for v in raw_df.iloc[idx].tolist()]
        if "วัน-เดือน-ปี" in row and "ชื่อผู้เบิก" in row:
            return idx
    return None


def _pick_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for col in df.columns:
        col_text = str(col).strip()
        for key in candidates:
            if key == col_text or key in col_text:
                return col
    return None


def _to_number(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "")
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    try:
        return float(text)
    except ValueError:
        return None


def _parse_amount_in_text(text: str) -> float | None:
    match = re.search(r"(-?\d[\d,]*(?:\.\d+)?)", text)
    if not match:
        return None
    raw = match.group(1).replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def _detect_category(detail: str, note: str) -> str:
    combined = f"{detail} {note}".lower()
    if any(keyword in combined for keyword in FINANCE_KEYWORDS):
        return "finance"
    if any(keyword in combined for keyword in CONTAINER_KEYWORDS):
        return "container"
    if any(keyword in combined for keyword in ADVANCE_KEYWORDS):
        return "advance"
    return "other"


def _parse_memo(name: str, detail: str, note: str) -> dict[str, Any]:
    merged = " ".join(part for part in (name, detail, note) if part).strip()
    lowered = merged.lower()
    has_deduction = "หัก" in merged
    amount_in_text = _parse_amount_in_text(merged)

    parsed_person = name.strip() if name else ""
    parsed_detail = detail.strip() if detail else ""
    if not parsed_person and merged:
        pieces = merged.split()
        parsed_person = pieces[0]
        parsed_detail = " ".join(pieces[1:])

    return {
        "memo_text": merged,
        "memo_has_deduction": has_deduction,
        "memo_amount_in_text": amount_in_text,
        "memo_contains_job_hint": any(keyword in lowered for keyword in ("ตู้", "job", "เบอร์ตู้", "เลขจ็อบ")),
        "parsed_person": parsed_person,
        "parsed_detail": parsed_detail,
    }


def _load_sheet_rows(site: str, workbook_path: Path, sheet_name: str) -> list[dict[str, Any]]:
    raw_df = pd.read_excel(workbook_path, sheet_name=sheet_name, header=None)
    header_idx = _find_header_row(raw_df)
    if header_idx is None:
        return []

    headers = raw_df.iloc[header_idx].fillna("").astype(str).str.strip().tolist()
    data_df = raw_df.iloc[header_idx + 1 :].copy()
    data_df.columns = headers

    date_col = _pick_column(data_df, ("วัน-เดือน-ปี",))
    name_col = _pick_column(data_df, ("ชื่อผู้เบิก",))
    detail_col = _pick_column(data_df, ("รายการ",))
    income_col = _pick_column(data_df, ("รายรับ",))
    expense_col = _pick_column(data_df, ("ยอดจ่าย",))
    deduction_col = _pick_column(data_df, ("พขร.เบิก หัก เงินเดือน",))
    balance_col = _pick_column(data_df, ("คงเหลือ",))
    note_col = _pick_column(data_df, ("หมายเหตุ",))

    rows: list[dict[str, Any]] = []
    for index, row in data_df.iterrows():
        date_raw = row[date_col] if date_col else None
        name = str(row[name_col]).strip() if name_col and pd.notna(row[name_col]) else ""
        detail = str(row[detail_col]).strip() if detail_col and pd.notna(row[detail_col]) else ""
        note = str(row[note_col]).strip() if note_col and pd.notna(row[note_col]) else ""

        if "ห้ามลบ หรือ แทรก หลัง จาก บรรทัดนี้" in name:
            break

        income = _to_number(row[income_col]) if income_col else None
        expense = _to_number(row[expense_col]) if expense_col else None
        deduction = _to_number(row[deduction_col]) if deduction_col else None
        balance = _to_number(row[balance_col]) if balance_col else None

        if not any([pd.notna(date_raw), name, detail, note, income, expense, deduction]):
            continue

        date_value = pd.to_datetime(date_raw, errors="coerce")
        # Keep only real ledger transactions; summary/control rows usually have no date.
        if pd.isna(date_value):
            continue

        memo_fields = _parse_memo(name=name, detail=detail, note=note)
        category = _detect_category(detail=detail, note=note)

        rows.append(
            {
                "site": site,
                "sheet_name": sheet_name,
                "source_row_index": int(index) + 1,
                "date": date_value.strftime("%Y-%m-%d") if pd.notna(date_value) else "",
                "name": name,
                "detail": detail,
                "note": note,
                "category": category,
                "income": income,
                "expense": expense,
                "deduct_salary": deduction,
                "balance": balance,
                **memo_fields,
            }
        )
    return rows


def build_dataset() -> pd.DataFrame:
    all_rows: list[dict[str, Any]] = []
    for site, workbook in SITE_WORKBOOKS.items():
        if not workbook.exists():
            continue
        xls = pd.ExcelFile(workbook)
        for sheet in xls.sheet_names:
            if sheet in IGNORED_SHEETS:
                continue
            all_rows.extend(_load_sheet_rows(site=site, workbook_path=workbook, sheet_name=sheet))
    return pd.DataFrame(all_rows)


def build_summary(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"record_count": 0, "sites": {}, "categories": {}}

    def safe_sum(series: pd.Series) -> float:
        return float(series.fillna(0).sum())

    site_summary: dict[str, Any] = {}
    for site, site_df in df.groupby("site"):
        site_summary[site] = {
            "rows": int(len(site_df)),
            "expense_total": safe_sum(site_df["expense"]),
            "deduct_salary_total": safe_sum(site_df["deduct_salary"]),
            "finance_rows": int((site_df["category"] == "finance").sum()),
        }

    category_summary: dict[str, Any] = {}
    for category, cat_df in df.groupby("category"):
        category_summary[category] = {
            "rows": int(len(cat_df)),
            "expense_total": safe_sum(cat_df["expense"]),
            "deduct_salary_total": safe_sum(cat_df["deduct_salary"]),
        }

    return {
        "record_count": int(len(df)),
        "sites": site_summary,
        "categories": category_summary,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dataset = build_dataset()
    if dataset.empty:
        raise SystemExit("No petty cash rows found. Check workbook structure.")

    dataset.sort_values(["site", "date", "sheet_name", "source_row_index"], inplace=True)

    csv_path = OUTPUT_DIR / "petty_cash_records.csv"
    json_path = OUTPUT_DIR / "petty_cash_records.json"
    summary_path = OUTPUT_DIR / "summary.json"

    dataset.to_csv(csv_path, index=False, encoding="utf-8-sig")
    json_path.write_text(dataset.to_json(orient="records", force_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(json.dumps(build_summary(dataset), ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Exported {len(dataset):,} rows")
    print(f"- {csv_path}")
    print(f"- {json_path}")
    print(f"- {summary_path}")


if __name__ == "__main__":
    main()
