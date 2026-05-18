# data_responsibility.py — PamojaData Data Responsibility Module
# Implements OCHA/IASC data responsibility principles for humanitarian data
# Reference: IASC Operational Guidance on Data Responsibility 2023

# ── PII FIELD DETECTOR ────────────────────────────────────────────────────────
# Common column names that may contain personally identifiable information
PII_KEYWORDS = [
    'name', 'names', 'firstname', 'lastname', 'surname',
    'id', 'national_id', 'passport', 'beneficiary_id',
    'phone', 'mobile', 'telephone', 'contact',
    'email', 'address', 'location', 'gps', 'coordinates',
    'lat', 'lon', 'latitude', 'longitude',
    'age', 'dob', 'date_of_birth', 'birthdate',
    'gender', 'sex', 'ethnicity', 'religion', 'nationality',
    'income', 'salary', 'bank', 'financial',
    'health', 'medical', 'diagnosis', 'disability',
    'refugee', 'idp', 'asylum', 'status',
    'village', 'household', 'hh_id', 'camp'
]

# Risk levels for different data types
PII_RISK_LEVELS = {
    'High': [
        'national_id', 'passport', 'phone', 'mobile', 'email',
        'gps', 'coordinates', 'lat', 'lon', 'health',
        'medical', 'diagnosis', 'income', 'bank', 'refugee',
        'asylum', 'religion', 'ethnicity'
    ],
    'Medium': [
        'name', 'names', 'firstname', 'lastname', 'surname',
        'address', 'village', 'household', 'hh_id', 'camp',
        'age', 'dob', 'date_of_birth', 'disability', 'status'
    ],
    'Low': [
        'gender', 'sex', 'nationality', 'location', 'salary'
    ]
}


def scan_for_pii(df):
    """
    Scans DataFrame column names for potential PII fields.
    Returns a list of flagged columns with risk levels.
    """
    flagged = []
    for col in df.columns:
        col_lower = col.lower().replace(' ', '_').replace('-', '_')
        for keyword in PII_KEYWORDS:
            if keyword in col_lower:
                risk = 'Low'
                for level, keywords in PII_RISK_LEVELS.items():
                    if keyword in keywords:
                        risk = level
                        break
                flagged.append({
                    'column': col,
                    'matched_keyword': keyword,
                    'risk_level': risk,
                    'recommendation': get_recommendation(risk, keyword)
                })
                break
    return flagged


def get_recommendation(risk_level, keyword):
    """Returns handling recommendation based on risk level."""
    if risk_level == 'High':
        return f"⛔ Remove or anonymise '{keyword}' before uploading. This is sensitive personal data."
    elif risk_level == 'Medium':
        return f"⚠️ Consider anonymising '{keyword}'. Use codes or aggregates instead of direct identifiers."
    else:
        return f"ℹ️ '{keyword}' is low risk but ensure data was collected with informed consent."


def get_consent_checklist():
    """
    Returns IASC data responsibility consent checklist items.
    Programme teams should confirm these before uploading data.
    """
    return [
        "Data was collected with informed consent from beneficiaries",
        "Beneficiaries were informed how their data would be used",
        "Data does not include unnecessary personal identifiers",
        "Data collection followed the organisation's data protection policy",
        "Sensitive data (health, protection, financial) has been anonymised",
        "Data sharing agreements are in place with all partners",
        "Data is stored securely and access is restricted to authorised staff",
        "Beneficiaries have the right to withdraw consent at any time"
    ]


def get_data_minimisation_tips():
    """
    Returns practical tips for data minimisation in M&E.
    """
    return [
        "Collect only the data you need — every extra field is a risk",
        "Use aggregated counts instead of individual records where possible",
        "Replace names with unique codes before uploading to digital systems",
        "Delete raw field data once aggregated indicators are calculated",
        "Never upload beneficiary lists, only programme statistics",
        "Use location codes (district, county) instead of GPS coordinates",
        "Separate personal data from programme data in different files"
    ]


def check_file_size(file, max_mb=10):
    """
    Checks if uploaded file exceeds size limit.
    Large files may contain more data than necessary.
    """
    max_bytes = max_mb * 1024 * 1024
    if hasattr(file, 'size') and file.size > max_bytes:
        return False, f"File size ({file.size / 1024 / 1024:.1f}MB) exceeds {max_mb}MB limit. Consider uploading aggregated data only."
    return True, "File size acceptable."


def generate_responsibility_summary(pii_flags, consent_checked):
    """
    Generates a data responsibility summary for the session.
    """
    high = sum(1 for f in pii_flags if f['risk_level'] == 'High')
    medium = sum(1 for f in pii_flags if f['risk_level'] == 'Medium')
    low = sum(1 for f in pii_flags if f['risk_level'] == 'Low')

    status = 'Pass' if high == 0 and consent_checked else 'Fail' if high > 0 else 'Warning'

    return {
        'status': status,
        'high_risk_fields': high,
        'medium_risk_fields': medium,
        'low_risk_fields': low,
        'consent_confirmed': consent_checked,
        'total_flags': len(pii_flags)
    }


def deep_scan_dataframe(df, sample_n=1000):
    """
    Performs a deeper scan for potential PII by checking both column names
    and a sample of cell values for keywords. Returns detailed flags.
    """
    import re
    flags = []

    # Column-name scan (reuse existing logic)
    col_flags = scan_for_pii(df)
    for f in col_flags:
        f['type'] = 'column_name'
        flags.append(f)

    # Sample up to `sample_n` rows for value scanning
    n = min(len(df), sample_n)
    if n == 0:
        return flags

    sample = df.sample(n=n) if len(df) > n else df

    # Build a regex of keywords to search in cell values (word boundaries)
    keywords = set(PII_KEYWORDS)
    pattern = re.compile(r"\b(" + r"|".join(re.escape(k) for k in keywords) + r")\b", flags=re.IGNORECASE)

    for col in sample.columns:
        count = 0
        for val in sample[col].astype(str):
            if pattern.search(val):
                count += 1
        if count > 0:
            # determine risk by keyword if possible (take first matched)
            matched = None
            for k in keywords:
                if k in col.lower():
                    matched = k
                    break
            risk = 'Medium'
            for level, kws in PII_RISK_LEVELS.items():
                if matched and matched in kws:
                    risk = level
                    break
            flags.append({
                'column': col,
                'matched_keyword': matched or 'value-match',
                'risk_level': risk,
                'sample_matches': int(count),
                'recommendation': get_recommendation(risk, matched or 'value-match'),
                'type': 'cell_value'
            })

    return flags