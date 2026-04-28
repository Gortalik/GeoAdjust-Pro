import pandas as pd
from pathlib import Path

excel_file = Path("test_real_mes/b_g/niv/GRO2209.xlsx")
xl = pd.ExcelFile(excel_file)
print("Имена листов:", xl.sheet_names)
for name in xl.sheet_names:
    print(f"  '{name}' (длина: {len(name)})")