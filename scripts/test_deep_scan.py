import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.responsibility.data_responsibility import deep_scan_dataframe
import pandas as pd

df = pd.DataFrame({
    'Name': ['Alice','Bob','Charlie'],
    'Phone': ['+12345','+23456','+34567'],
    'Amount': ['100','200','300'],
    'Notes': ['no issues','has passport 1234','lives in village']
})
res = deep_scan_dataframe(df, sample_n=3)
print('Deep scan results:')
import json
print(json.dumps(res, indent=2))
