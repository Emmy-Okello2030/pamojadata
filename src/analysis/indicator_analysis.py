# indicator_analysis.py — PamojaData Analysis Engine
# Core calculations for indicator performance across all programmes

import pandas as pd
import numpy as np


def calculate_achievement(df, mapping):
    """
    Calculates variance, % achievement and status for each indicator.
    """
    df = df.copy()

    # Ensure numeric
    df[mapping['target']] = pd.to_numeric(df[mapping['target']], errors='coerce').fillna(0)
    df[mapping['achieved']] = pd.to_numeric(df[mapping['achieved']], errors='coerce').fillna(0)

    # Core calculations
    df['Variance'] = df[mapping['achieved']] - df[mapping['target']]
    df['% Achievement'] = df.apply(
        lambda row: round((row[mapping['achieved']] / row[mapping['target']]) * 100, 1)
        if row[mapping['target']] > 0 else 0, axis=1
    )

    # Status flagging
    def flag_status(pct):
        if pct >= 100:
            return "✅ Met/Exceeded"
        elif pct >= 80:
            return "🟡 On Track"
        else:
            return "🔴 Off Track"

    df['Status'] = df['% Achievement'].apply(flag_status)
    return df


def sector_summary(df, mapping):
    """
    Aggregates performance by sector.
    """
    summary = df.groupby(mapping['sector']).agg(
        Total_Target=(mapping['target'], 'sum'),
        Total_Achieved=(mapping['achieved'], 'sum'),
        Indicators=(mapping['indicator_name'], 'count')
    ).reset_index()

    summary['% Achievement'] = (
        summary['Total_Achieved'] / summary['Total_Target'] * 100
    ).round(1)

    summary['Status'] = summary['% Achievement'].apply(
        lambda x: "✅ Met/Exceeded" if x >= 100
        else "🟡 On Track" if x >= 80
        else "🔴 Off Track"
    )
    return summary


def period_summary(df, mapping):
    """
    Aggregates performance by reporting period.
    Enables trend analysis across multiple cycles.
    """
    if not mapping.get('period') or mapping['period'] not in df.columns:
        return None

    summary = df.groupby(mapping['period']).agg(
        Total_Target=(mapping['target'], 'sum'),
        Total_Achieved=(mapping['achieved'], 'sum')
    ).reset_index()

    summary['% Achievement'] = (
        summary['Total_Achieved'] / summary['Total_Target'] * 100
    ).round(1)

    return summary


def location_summary(df, mapping):
    """
    Aggregates performance by location/region.
    Geographic disaggregation for field-level insights.
    """
    if not mapping.get('location') or mapping['location'] not in df.columns:
        return None

    summary = df.groupby(mapping['location']).agg(
        Total_Target=(mapping['target'], 'sum'),
        Total_Achieved=(mapping['achieved'], 'sum'),
        Indicators=(mapping['indicator_name'], 'count')
    ).reset_index()

    summary['% Achievement'] = (
        summary['Total_Achieved'] / summary['Total_Target'] * 100
    ).round(1)

    return summary


def sector_period_trend(df, mapping):
    """
    Cross-tabulates sector performance across reporting periods.
    Powers the trend chart in the dashboard.
    """
    if not mapping.get('period') or mapping['period'] not in df.columns:
        return None

    trend = df.groupby([mapping['period'], mapping['sector']]).agg(
        Total_Target=(mapping['target'], 'sum'),
        Total_Achieved=(mapping['achieved'], 'sum')
    ).reset_index()

    trend['% Achievement'] = (
        trend['Total_Achieved'] / trend['Total_Target'] * 100
    ).round(1)

    return trend


def overall_summary(df, mapping):
    """
    Returns headline KPIs for the dashboard summary cards.
    """
    total = len(df)
    met = len(df[df['Status'] == "✅ Met/Exceeded"])
    on_track = len(df[df['Status'] == "🟡 On Track"])
    off_track = len(df[df['Status'] == "🔴 Off Track"])

    total_target = df[mapping['target']].sum()
    total_achieved = df[mapping['achieved']].sum()
    overall_pct = round((total_achieved / total_target * 100), 1) if total_target > 0 else 0

    return {
        'total_indicators': total,
        'met': met,
        'on_track': on_track,
        'off_track': off_track,
        'overall_achievement': overall_pct,
        'total_target': total_target,
        'total_achieved': total_achieved
    }


def get_off_track(df):
    """Returns only off track indicators."""
    return df[df['Status'] == "🔴 Off Track"].copy()


def get_top_performers(df, mapping, n=3):
    """Returns top n performing indicators by % achievement."""
    return df.nlargest(n, '% Achievement')[[
        mapping['indicator_name'],
        mapping['sector'],
        '% Achievement',
        'Status'
    ]]


def get_bottom_performers(df, mapping, n=3):
    """Returns bottom n performing indicators by % achievement."""
    return df.nsmallest(n, '% Achievement')[[
        mapping['indicator_name'],
        mapping['sector'],
        '% Achievement',
        'Status'
    ]]