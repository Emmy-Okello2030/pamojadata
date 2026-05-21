import pandas as pd
import numpy as np

def calculate_achievement(df, mapping):
    df = df.copy()
    df[mapping['target']] = pd.to_numeric(df[mapping['target']], errors='coerce').fillna(0)
    df[mapping['achieved']] = pd.to_numeric(df[mapping['achieved']], errors='coerce').fillna(0)
    df['Variance'] = df[mapping['achieved']] - df[mapping['target']]
    df['% Achievement'] = df.apply(
        lambda row: round((row[mapping['achieved']] / row[mapping['target']]) * 100, 1)
        if row[mapping['target']] > 0 else 0, axis=1
    )
    def flag_status(pct):
        if pct >= 100: return "? Met/Exceeded"
        elif pct >= 80: return "?? On Track"
        return "?? Off Track"
    df['Status'] = df['% Achievement'].apply(flag_status)
    return df

def sector_summary(df, mapping):
    # Use temporary names to avoid "already exists" errors during reset_index
    summary = df.groupby(mapping['sector']).agg(
        _t1=(mapping['target'], 'sum'),
        _t2=(mapping['achieved'], 'sum'),
        _t3=(mapping['indicator_name'], 'count')
    ).reset_index()
    summary = summary.rename(columns={'_t1': 'Total_Target', '_t2': 'Total_Achieved', '_t3': 'Indicators'})
    summary['% Achievement'] = (summary['Total_Achieved'] / summary['Total_Target'] * 100).round(1)
    summary['Status'] = summary['% Achievement'].apply(lambda x: "? Met/Exceeded" if x >= 100 else "?? On Track" if x >= 80 else "?? Off Track")
    return summary

def sector_period_trend(df, mapping):
    if not mapping.get('period') or mapping['period'] not in df.columns:
        return None
    p_col, s_col = mapping['period'], mapping['sector']
    # If period and sector are the same column, group by one to avoid duplicate column error
    group_cols = [p_col] if p_col == s_col else [p_col, s_col]
    trend = df.groupby(group_cols).agg(
        _t1=(mapping['target'], 'sum'),
        _t2=(mapping['achieved'], 'sum')
    ).reset_index()
    trend = trend.rename(columns={'_t1': 'Total_Target', '_t2': 'Total_Achieved'})
    if s_col not in trend.columns: trend[s_col] = trend[p_col]
    trend['% Achievement'] = (trend['Total_Achieved'] / trend['Total_Target'] * 100).round(1)
    return trend

def overall_summary(df, mapping):
    total = len(df)
    met = len(df[df['Status'] == "? Met/Exceeded"])
    on_track = len(df[df['Status'] == "?? On Track"])
    off_track = len(df[df['Status'] == "?? Off Track"])
    total_target = df[mapping['target']].sum()
    total_achieved = df[mapping['achieved']].sum()
    overall_pct = round((total_achieved / total_target * 100), 1) if total_target > 0 else 0
    return {'total_indicators': total, 'met': met, 'on_track': on_track, 'off_track': off_track, 'overall_achievement': overall_pct, 'total_target': total_target, 'total_achieved': total_achieved}

# (Other functions remain the same)
def period_summary(df, mapping):
    if not mapping.get('period') or mapping['period'] not in df.columns: return None
    summary = df.groupby(mapping['period']).agg(_t1=(mapping['target'], 'sum'), _t2=(mapping['achieved'], 'sum')).reset_index()
    summary = summary.rename(columns={'_t1': 'Total_Target', '_t2': 'Total_Achieved'})
    summary['% Achievement'] = (summary['Total_Achieved'] / summary['Total_Target'] * 100).round(1)
    return summary

def location_summary(df, mapping):
    if not mapping.get('location') or mapping['location'] not in df.columns: return None
    summary = df.groupby(mapping['location']).agg(_t1=(mapping['target'], 'sum'), _t2=(mapping['achieved'], 'sum'), _t3=(mapping['indicator_name'], 'count')).reset_index()
    summary = summary.rename(columns={'_t1': 'Total_Target', '_t2': 'Total_Achieved', '_t3': 'Indicators'})
    summary['% Achievement'] = (summary['Total_Achieved'] / summary['Total_Target'] * 100).round(1)
    return summary

def get_off_track(df): return df[df['Status'] == "?? Off Track"].copy()
def get_top_performers(df, mapping, n=3): return df.nlargest(n, '% Achievement')[[mapping['indicator_name'], mapping['sector'], '% Achievement', 'Status']]
def get_bottom_performers(df, mapping, n=3): return df.nsmallest(n, '% Achievement')[[mapping['indicator_name'], mapping['sector'], '% Achievement', 'Status']]
