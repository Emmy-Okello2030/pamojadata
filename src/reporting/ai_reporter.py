# ai_reporter.py — PamojaData AI Reporting Engine
# Uses Google Gemini API to generate professional donor narratives
# Tailored to specific donor styles and programme context

import requests
import streamlit as st
import os

# Gemini API settings
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# Donor-specific writing guidelines
DONOR_GUIDELINES = {
    "General": "Use clear, professional language focused on results and beneficiary impact.",
    "USAID": "Align with USAID's results framework. Emphasize sustainability, local ownership, and development hypothesis. Use active voice.",
    "EU": "Follow EU results-based reporting. Reference logical framework (logframe) outputs and outcomes. Include value for money references.",
    "UN": "Use UN reporting conventions. Reference SDG alignment where relevant. Emphasize human rights-based approach and leave no one behind.",
    "Global Fund": "Focus on disease burden reduction, health system strengthening, and value for money metrics.",
    "Gates Foundation": "Emphasize innovation, evidence-based approaches, and scalability of interventions."
}


def get_api_key():
    """Reads Gemini API key securely from Streamlit secrets or environment variable."""
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        return api_key


def call_gemini(prompt, max_tokens=2000):
    """
    Makes a request to the Gemini API.
    Returns the generated text or an error message.
    """
    try:
        api_key = get_api_key()
    except ValueError as e:
        return f"⚠️ Configuration error: {str(e)}"

    url = GEMINI_API_URL
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.7,
            "topP": 0.9
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    except requests.exceptions.HTTPError as e:
        if response.status_code == 400:
            return "⚠️ API Error 400: Bad Request. Check that your API key is valid and enabled for the Gemini API."
        elif response.status_code == 401:
            return "⚠️ API Error 401: Unauthorized. Your API key may be invalid or revoked."
        elif response.status_code == 429:
            return "⚠️ API Error 429: Rate limit exceeded. Please try again later."
        return f"⚠️ API Error {response.status_code}: {str(e)}"
    except requests.exceptions.ConnectionError:
        return "⚠️ Connection failed. Check your internet connection and try again."
    except KeyError:
        return "⚠️ Unexpected response format from Gemini API."
    except Exception as e:
        return f"⚠️ Unexpected error: {str(e)}"


def build_prompt(analyzed_df, sector_summary, overall_summary,
                 donor_type, qualitative_notes, org_name, report_period,
                 risk_summary=None):
    """
    Builds a rich, context-aware prompt for Gemini.
    """
    donor_guideline = DONOR_GUIDELINES.get(donor_type, DONOR_GUIDELINES["General"])
    indicator_text = analyzed_df.to_string(index=False)
    sector_text = sector_summary.to_string(index=False)

    risk_section = ""
    if risk_summary:
        risk_section = f"""
Early Warning Risk Assessment:
- High Risk Indicators: {risk_summary['high_risk']}
- Medium Risk Indicators: {risk_summary['medium_risk']}
- Low Risk Indicators: {risk_summary['low_risk']}

Please reference the risk assessment in your recommendations section.
"""

    qualitative_section = ""
    if qualitative_notes and qualitative_notes.strip():
        qualitative_section = f"""
Field Notes & Qualitative Context (from programme team):
{qualitative_notes}

Incorporate these field insights naturally into the narrative where relevant.
"""

    prompt = f"""You are a senior M&E specialist writing a donor progress report for {org_name}.
Reporting Period: {report_period if report_period else 'Current Period'}
Donor: {donor_type}
Writing Guidelines: {donor_guideline}

Programme Performance Summary:
- Total Indicators: {overall_summary['total_indicators']}
- Overall Achievement Rate: {overall_summary['overall_achievement']}%
- Indicators Met/Exceeded: {overall_summary['met']}
- Indicators On Track: {overall_summary['on_track']}
- Indicators Off Track: {overall_summary['off_track']}
- Total Beneficiaries Reached: {int(overall_summary['total_achieved']):,}
- Total Target Beneficiaries: {int(overall_summary['total_target']):,}

Detailed Indicator Data:
{indicator_text}

Sector Performance:
{sector_text}
{risk_section}
{qualitative_section}

Write a professional donor report narrative with these exact sections:

## 1. Executive Summary
2-3 paragraphs. High-level overview of programme performance, headline achievements, and any critical issues.

## 2. Key Achievements
Highlight top performing indicators and sectors with specific numbers. Make it human — not just statistics.

## 3. Challenges & Mitigation Measures
For each off-track indicator, explain plausible operational reasons and corrective actions being taken.

## 4. Risk Assessment & Early Warnings
Highlight indicators showing early warning signs and recommend proactive measures.

## 5. Recommendations & Next Steps
3-5 concrete, actionable recommendations for the next reporting period.

## 6. Conclusion
One strong closing paragraph reaffirming commitment to programme goals and beneficiaries.

Tone: Professional, transparent, results-oriented, and human.
Format: Full paragraphs only — no bullet points in the narrative body.
"""
    return prompt


def generate_narrative(analyzed_df, sector_summary, overall_summary,
                       donor_type="General", qualitative_notes="",
                       org_name="Our Organisation", report_period="",
                       risk_summary=None):
    """
    Generates full donor narrative using Gemini API.
    """
    prompt = build_prompt(
        analyzed_df, sector_summary, overall_summary,
        donor_type, qualitative_notes, org_name, report_period,
        risk_summary
    )
    return call_gemini(prompt, max_tokens=2000)


def generate_executive_brief(overall_summary, sector_summary,
                              org_name, report_period, donor_type):
    """
    Generates a short executive brief for senior leadership.
    """
    sector_text = sector_summary.to_string(index=False)

    prompt = f"""Write a concise one-page executive brief for {org_name} senior leadership.
Reporting Period: {report_period}
Donor: {donor_type}

Performance:
- Overall Achievement: {overall_summary['overall_achievement']}%
- Indicators Met: {overall_summary['met']} of {overall_summary['total_indicators']}
- Off Track: {overall_summary['off_track']}

Sector Performance:
{sector_text}

Write 3 short paragraphs:
1. Headline performance (2-3 sentences)
2. Key wins and concerns (3-4 sentences)
3. Immediate actions needed (2-3 sentences)

Keep it sharp, direct, and leadership-ready. No section headers needed."""

    return call_gemini(prompt, max_tokens=600)