# quality_checks.py — PamojaData Data Quality Engine
# Automatically detects and flags data quality issues in programme data

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

def check_missing_values(df, mapping):
    """Flags rows with missing critical fields."""
    issues = []
    critical_fields = [
        mapping['indicator_name'],
        mapping['target'],
        mapping['achieved'],
        mapping['sector']
    ]
    for field in critical_fields:
        missing = df[field].isna().sum()
        if missing > 0:
            issues.append({
                'type': 'Missing Value',
                'description': f"{missing} missing values in '{field}' column",
                'severity': 'High' if field in [mapping['indicator_name'], mapping['target']] else 'Medium'
            })
    return issues


def check_duplicates(df, mapping):
    """Flags duplicate indicator + period combinations."""
    issues = []
    subset = [mapping['indicator_name']]
    if mapping.get('period') and mapping['period'] in df.columns:
        subset.append(mapping['period'])

    dupes = df.duplicated(subset=subset, keep=False)
    if dupes.any():
        issues.append({
            'type': 'Duplicate Records',
            'description': f"{dupes.sum()} duplicate rows found (same indicator + period)",
            'severity': 'High'
        })
    return issues


def check_negative_values(df, mapping):
    """Flags negative targets or achieved values."""
    issues = []
    for field in [mapping['target'], mapping['achieved']]:
        df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0)
        negatives = (df[field] < 0).sum()
        if negatives > 0:
            issues.append({
                'type': 'Negative Values',
                'description': f"{negatives} negative values found in '{field}' — targets and achieved must be positive",
                'severity': 'High'
            })
    return issues


def check_achievement_outliers(df, mapping):
    """
    Uses Isolation Forest ML model to detect statistical outliers
    in achievement rates — flags unusually high or low values.
    """
    issues = []
    df = df.copy()
    df[mapping['target']] = pd.to_numeric(df[mapping['target']], errors='coerce').fillna(0)
    df[mapping['achieved']] = pd.to_numeric(df[mapping['achieved']], errors='coerce').fillna(0)

    # Calculate achievement rate
    df['achievement_rate'] = df.apply(
        lambda row: row[mapping['achieved']] / row[mapping['target']]
        if row[mapping['target']] > 0 else 0, axis=1
    )

    # Need at least 5 rows for Isolation Forest
    if len(df) >= 5:
        model = IsolationForest(contamination=0.1, random_state=42)
        df['anomaly'] = model.fit_predict(df[['achievement_rate']])
        outliers = df[df['anomaly'] == -1]

        if not outliers.empty:
            outlier_names = outliers[mapping['indicator_name']].tolist()
            issues.append({
                'type': 'Statistical Outlier',
                'description': f"Unusual achievement rates detected in: {', '.join(map(str, outlier_names))}. Please verify these figures.",
                'severity': 'Medium'
            })
    return issues


def check_zero_targets(df, mapping):
    """Flags indicators with zero targets."""
    issues = []
    df[mapping['target']] = pd.to_numeric(df[mapping['target']], errors='coerce').fillna(0)
    zeros = (df[mapping['target']] == 0).sum()
    if zeros > 0:
        issues.append({
            'type': 'Zero Target',
            'description': f"{zeros} indicators have a target of 0 — this will affect achievement calculations",
            'severity': 'Medium'
        })
    return issues


def check_extreme_overachievement(df, mapping):
    """Flags indicators with suspiciously high achievement (>200%)."""
    issues = []
    df = df.copy()
    df[mapping['target']] = pd.to_numeric(df[mapping['target']], errors='coerce').fillna(0)
    df[mapping['achieved']] = pd.to_numeric(df[mapping['achieved']], errors='coerce').fillna(0)

    extreme = df[
        (df[mapping['target']] > 0) &
        (df[mapping['achieved']] / df[mapping['target']] > 2)
    ]
    if not extreme.empty:
        names = extreme[mapping['indicator_name']].tolist()
        issues.append({
            'type': 'Extreme Overachievement',
            'description': f"Achievement over 200% detected in: {', '.join(map(str, names))}. Verify data accuracy.",
            'severity': 'Medium'
        })
    return issues


def run_all_checks(df, mapping):
    """
    Runs all quality checks and returns a consolidated report.
    """
    all_issues = []
    all_issues.extend(check_missing_values(df, mapping))
    all_issues.extend(check_duplicates(df, mapping))
    all_issues.extend(check_negative_values(df, mapping))
    all_issues.extend(check_achievement_outliers(df, mapping))
    all_issues.extend(check_zero_targets(df, mapping))
    all_issues.extend(check_extreme_overachievement(df, mapping))

    # Summary
    high = sum(1 for i in all_issues if i['severity'] == 'High')
    medium = sum(1 for i in all_issues if i['severity'] == 'Medium')

    return {
        'issues': all_issues,
        'total': len(all_issues),
        'high': high,
        'medium': medium,
        'passed': len(all_issues) == 0
    }


def clean_data(df, mapping):
    """
    Auto-fixes what can be fixed and returns cleaned df.
    """
    df = df.copy()

    # Convert to numeric
    for col in [mapping['target'], mapping['achieved']]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        df[col] = df[col].abs()  # Fix negatives

    # Fill missing sector
    if df[mapping['sector']].isna().any():
        df[mapping['sector']] = df[mapping['sector']].fillna('Unspecified')

    # Drop full duplicates
    df = df.drop_duplicates()

    return df