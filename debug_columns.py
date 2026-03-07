import pandas as pd
import os

files = [
    r'c:\Users\user\Downloads\r2b\summary.xlsx',
    r'c:\Users\user\Downloads\r2b\OOS1.xlsx',
    r'c:\Users\user\Downloads\r2b\reconciliation.xlsx'
]

for f in files:
    if os.path.exists(f):
        print(f"--- Columns in {os.path.basename(f)} ---")
        try:
            df = pd.read_excel(f, nrows=5)
            print(list(df.columns))
            # Print first row to see data samples
            print("First row sample:")
            print(df.iloc[0].to_dict())
        except Exception as e:
            print(f"Error reading {f}: {e}")
    else:
        print(f"File not found: {f}")
