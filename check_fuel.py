import pandas as pd
import os
import glob
import string
from datetime import datetime, timedelta

# --- SETTINGS ---
TARGET_NAME = "นายพงษ์พันธ์ ทุมเชียงเข้ม"  # ชื่อที่ต้องการตรวจสอบ
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def col_idx_to_letter(idx):
    try: return string.ascii_uppercase[idx]
    except: return str(idx)

def letter_to_col_idx(letter):
    try: return string.ascii_uppercase.index(letter.upper().strip())
    except: return 0

def clean_number(value):
    try: return float(str(value).replace(',', '').strip()) if not pd.isna(value) else 0
    except: return 0

def parse_thai_date(date_str):
    if pd.isna(date_str) or isinstance(date_str, datetime): return date_str
    thai_months = {'ม.ค.': 1, 'ก.พ.': 2, 'มี.ค.': 3, 'เม.ย.': 4, 'พ.ค.': 5, 'มิ.ย.': 6, 'ก.ค.': 7, 'ส.ค.': 8, 'ก.ย.': 9, 'ต.ค.': 10, 'พ.ย.': 11, 'ธ.ค.': 12}
    try:
        parts = str(date_str).strip().split()
        if len(parts) >= 3:
            day, month, year = int(parts[0]), thai_months.get(parts[1]), int(parts[2])
            return datetime(year + (2500 if year < 100 else 0) - 543, month, day)
    except: pass
    return pd.to_datetime(date_str, errors='coerce')

def main():
    print(f"🔧 เครื่องมือเจาะดูไฟล์น้ำมัน (Manual Inspector)")
    print(f"🔍 เป้าหมาย: {TARGET_NAME}")
    
    # 1. เลือกไฟล์
    files = [f for f in glob.glob(os.path.join(BASE_DIR, "*.xlsx")) if not os.path.basename(f).startswith('~$')]
    for i, f in enumerate(files): print(f" [{i+1}] {os.path.basename(f)}")
    f_idx = int(input("เลือกไฟล์น้ำมันเบอร์: ")) - 1
    f_path = files[f_idx]

    # 2. อ่านไฟล์แบบดิบๆ (เพื่อหาหัวข้อ)
    xl = pd.ExcelFile(f_path)
    sheet_name = xl.sheet_names[0] # เอา Sheet แรก
    df_preview = pd.read_excel(f_path, sheet_name=sheet_name, header=None, nrows=15)
    
    print(f"\n📄 ตัวอย่างข้อมูล 15 บรรทัดแรกของไฟล์ '{os.path.basename(f_path)}':")
    print("-" * 80)
    # Print header letters
    col_str = "    " + " ".join([f"{col_idx_to_letter(i):<10}" for i in range(len(df_preview.columns))])
    print(col_str)
    print("-" * 80)
    
    for idx, row in df_preview.iterrows():
        # Print row number and data
        row_str = f"[{idx+1:2}] " + " ".join([f"{str(val)[:10]:<10}" for val in row.values])
        print(row_str)
    print("-" * 80)

    # 3. ให้คนใส่ค่าเอง (Manual Input)
    header_row = int(input("👉 บรรทัดที่เป็น 'หัวข้อ' (เช่น 1, 3, 5): ")) - 1
    
    print("\nระบุคอลัมน์เป็นตัวอักษร (เช่น A, B, C)")
    col_name_l = input("  - คอลัมน์ 'ชื่อคนขับ' คือช่อง?: ")
    col_date_l = input("  - คอลัมน์ 'วันที่'    คือช่อง?: ")
    col_amt_l  = input("  - คอลัมน์ 'ยอดเงิน'   คือช่อง?: ")

    c_name = letter_to_col_idx(col_name_l)
    c_date = letter_to_col_idx(col_date_l)
    c_amt  = letter_to_col_idx(col_amt_l)

    # 4. โหลดข้อมูลจริงตามที่ระบุ
    df = pd.read_excel(f_path, sheet_name=sheet_name, header=header_row)
    
    # 5. รับวันตัดรอบ
    cutoff_str = input("\n📅 วันตัดรอบ (วว/ดด/ปปปป): ")
    try: 
        cutoff_dt = datetime.strptime(cutoff_str, "%d/%m/%Y")
        last_month = cutoff_dt - pd.DateOffset(months=1)
        start_dt = last_month.replace(day=16)
        print(f"👉 ช่วงเวลา: {start_dt.strftime('%d/%m/%Y')} - {cutoff_dt.strftime('%d/%m/%Y')}")
    except: print("❌ วันที่ผิด"); return

    # 6. วนลูปเช็คยอด
    print(f"\n📋 รายการน้ำมันของ '{TARGET_NAME}' ในช่วงเวลา:")
    print("-" * 65)
    print(f"{'วันที่':<12} | {'ยอดเงิน':>10} | {'ชื่อในไฟล์'}")
    print("-" * 65)

    total = 0
    count = 0
    
    for index, row in df.iterrows():
        try:
            raw_name = str(row.iloc[c_name])
            if TARGET_NAME in raw_name: # เช็คชื่อ
                d_val = parse_thai_date(row.iloc[c_date])
                
                if pd.isna(d_val): continue

                amt = clean_number(row.iloc[c_amt])
                
                # เช็คช่วงวันที่
                if start_dt <= d_val <= cutoff_dt:
                    print(f"{d_val.strftime('%d/%m/%Y'):<12} | {amt:,.2f} | {raw_name}")
                    total += amt
                    count += 1
                
                # DEBUG: เช็ครายการที่หลุดช่วงไปนิดเดียว (3 วันหน้า-หลัง)
                elif (d_val >= start_dt - timedelta(days=3)) and (d_val <= cutoff_dt + timedelta(days=3)):
                     print(f"{d_val.strftime('%d/%m/%Y'):<12} | *{amt:,.2f} | {raw_name} (❌ อยู่นอกรอบ)")
        except Exception as e:
            continue

    print("-" * 65)
    print(f"✅ ยอดรวมที่ V.17 เห็น: {total:,.2f} บาท (จำนวน {count} รายการ)")
    print("-" * 65)

if __name__ == "__main__":
    main()