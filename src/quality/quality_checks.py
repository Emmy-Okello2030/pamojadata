import pandas as pd
import numpy as np

def get_quality_summary(df, mapping):
    """Returns a high-level summary of data quality for app.py"""
    results = run_all_checks(df, mapping)
    score = 100 - (results.get('total', 0) * 5)
    return {
        'score': max(0, score),
        'total_issues': results.get('total', 0),
        'status': 'Pass' if results.get('passed') else 'Fail'
    }

def run_all_checks(df, mapping):
    """Consolidated check logic"""
    issues = []
    if mapping.get('target') in df.columns:
        m = df[mapping['target']].isna().sum()
        if m > 0: issues.append({'type': 'Missing', 'description': f'{m} missing targets'})
    return {'issues': issues, 'total': len(issues), 'passed': len(issues) == 0}

def clean_data(df, mapping):
    """The smart cleaner we just built"""
    df_clean = df.copy()
    for col in [mapping.get('target'), mapping.get('achieved')]:
        if col and col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0).abs()
    for col in [mapping.get('indicator_name'), mapping.get('sector')]:
        if col and col in df_clean.columns:
            df_clean[col] = df_clean[col].fillna('Unspecified').astype(str)
    return df_clean.drop_duplicates().apply(lambda x: x.str.strip() if x.dtype == "object" else x)

class QualityChecker:
    def __init__(self, df=None, mapping=None):
        self.df = df
        self.mapping = mapping
    def run_all(self):
        return run_all_checks(self.df, self.mapping)
