import pandas as pd
from pathlib import Path


def main() -> None:
    excel_path = Path(r"C:\Users\Home\Desktop\Project YK\รายการรับเช็ค AYU 2025-2026.xlsx")
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    output_dir = excel_path.parent / "AYU_sheets_csv"
    output_dir.mkdir(exist_ok=True)

    # Load all sheets as a dict: {sheet_name: DataFrame}
    sheets = pd.read_excel(excel_path, sheet_name=None)

    for sheet_name, df in sheets.items():
        safe_name = "".join(
            c if c.isalnum() or c in " _-" else "_"
            for c in str(sheet_name)
        )
        csv_path = output_dir / f"{safe_name}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"Saved: {csv_path}")


if __name__ == "__main__":
    main()

