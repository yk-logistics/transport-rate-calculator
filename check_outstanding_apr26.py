import glob
import numpy as np
import pandas as pd


def main() -> None:
    matches = glob.glob(r"C:\Users\Home\Downloads\Copy of YK Outstanding Apr*26.xlsx")
    if not matches:
        raise FileNotFoundError("Target file not found")

    path = matches[0]
    xls = pd.ExcelFile(path)
    print(f"file={path}")
    print(f"sheets={xls.sheet_names}")

    target_sheets = ["Balance Sep'25", "Balance Jan'26", "Balance Feb'26", "Balance Apr'26"]
    for sheet in target_sheets:
        if sheet not in xls.sheet_names:
            continue
        df = pd.read_excel(path, sheet_name=sheet, header=None)
        print(f"\n=== {sheet} ===")
        for i, row in df.iterrows():
            vals = []
            for v in row.tolist():
                if isinstance(v, float) and np.isnan(v):
                    continue
                vals.append(v)
            if vals:
                shown = " | ".join(str(v) for v in vals[:10])
                print(f"{i+1}| {shown}")


if __name__ == "__main__":
    main()

