import pandas as pd
from pathlib import Path
from datetime import datetime


def parse_month_from_filename(path: Path) -> datetime:
    """
    Filenames are like 'Jan 25.csv', 'Feb 26.csv'.
    Interpret '25' as 2025, '26' as 2026, etc.
    """
    stem = path.stem  # e.g. "Jan 25"
    try:
        dt = datetime.strptime(stem, "%b %y")
    except ValueError:
        # If parsing fails, put very old date so it appears first but flagged
        dt = datetime(1900, 1, 1)
    return dt


def main() -> None:
    base_dir = Path(r"C:\Users\Home\Desktop\Project YK\AYU_sheets_csv")
    if not base_dir.exists():
        raise FileNotFoundError(f"Directory not found: {base_dir}")

    rows = []

    for csv_path in sorted(base_dir.glob("*.csv")):
        month_dt = parse_month_from_filename(csv_path)

        try:
            # Use third row (0-based index 2) as header to skip title rows
            df = pd.read_csv(csv_path, header=2)
        except Exception as exc:
            print(f"Skip {csv_path.name}: cannot read ({exc})")
            continue

        # Normalize column names (strip spaces and BOM)
        df.columns = [
            str(c).replace("\ufeff", "").strip() for c in df.columns
        ]

        if "ชื่อบริษัท" not in df.columns or "เงินหน้าเช็ค" not in df.columns:
            continue

        # Only count BigC XD and BigC TB (exclude BPD and others),
        # except for Mar 26 where we partially include BPD.
        company_col = df["ชื่อบริษัท"].astype(str)
        mask_xd_tb = company_col.str.contains("DHL บิ๊กซี XD", na=False) | company_col.str.contains(
            "DHL บิ๊กซี TB", na=False
        )
        if not mask_xd_tb.any() and csv_path.stem != "Mar 26":
            continue

        money_series = pd.to_numeric(
            df.loc[mask_xd_tb, "เงินหน้าเช็ค"], errors="coerce"
        )
        bigc_sum = money_series.sum()

        # Special rule: for Mar 26, include BPD but subtract 309,135.98
        if csv_path.stem == "Mar 26":
            mask_bpd = company_col.str.contains("DHL บิ๊กซี BPD", na=False)
            if mask_bpd.any():
                bpd_series = pd.to_numeric(
                    df.loc[mask_bpd, "เงินหน้าเช็ค"], errors="coerce"
                )
                bpd_sum = bpd_series.sum()
                adj_bpd = max(bpd_sum - 309135.98, 0)
                bigc_sum += adj_bpd
        rows.append(
            {
                "month_label": csv_path.stem,
                "month": month_dt,
                "bigc_revenue": float(bigc_sum),
            }
        )

    if not rows:
        print("No BigC rows found.")
        return

    rows.sort(key=lambda r: r["month"])

    print("BigC revenue by month (front of cheque):")
    for r in rows:
        print(
            f"- {r['month_label']}: {r['bigc_revenue']:,.2f} THB"
        )

    # Simple averages
    revenues = [r["bigc_revenue"] for r in rows]
    overall_avg = sum(revenues) / len(revenues)
    recent_3_avg = sum(revenues[-3:]) / min(3, len(revenues))

    print()
    print(f"Overall average per month: {overall_avg:,.2f} THB")
    print(f"Last 3 months average:    {recent_3_avg:,.2f} THB")


if __name__ == "__main__":
    main()

