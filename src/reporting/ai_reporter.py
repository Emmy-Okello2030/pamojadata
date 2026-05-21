# ai_reporter.py — PamojaData AI Reporting Engine
# Supports Google Gemini, Groq and OpenRouter with automatic fallback
# If one API fails or hits rate limits, automatically tries the next one

import time
import requests
import streamlit as st
import os

# ── MODEL SETTINGS ────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.0-flash-lite"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

OPENROUTER_MODEL = "mistralai/mistral-7b-instruct:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# Donor-specific writing guidelines
DONOR_GUIDELINES = {
    "General": "Use clear, professional language focused on results and beneficiary impact.",
    "USAID": "Align with USAID's results framework. Emphasize sustainability, local ownership, and development hypothesis. Use active voice.",
    "EU": "Follow EU results-based reporting. Reference logical framework (logframe) outputs and outcomes. Include value for money references.",
    "UN": "Use UN reporting conventions. Reference SDG alignment where relevant. Emphasize human rights-based approach and leave no one behind.",
    "Global Fund": "Focus on disease burden reduction, health system strengthening, and value for money metrics.",
    "Gates Foundation": "Emphasize innovation, evidence-based approaches, and scalability of interventions."
}


# ── API KEY HELPERS ───────────────────────────────────────────────────────────

def get_gemini_key():
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
        if key: return key
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "")


def get_groq_key():
    try:
        key = st.secrets.get("GROQ_API_KEY", "")
        if key: return key
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY", "")


def get_openrouter_key():
    try:
        key = st.secrets.get("OPENROUTER_API_KEY", "")
        if key: return key
    except Exception:
        pass
    return os.environ.get("OPENROUTER_API_KEY", "")


# ── INDIVIDUAL API CALLERS ────────────────────────────────────────────────────

def call_gemini(prompt, max_tokens=1500, retries=2, retry_delay=15):
    """Calls Google Gemini API with retry on rate limit."""
    api_key = get_gemini_key()
    if not api_key:
        return None, "No Gemini API key configured."

    url = f"{GEMINI_BASE_URL}/{GEMINI_MODEL}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.7,
            "topP": 0.9
        }
    }

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            return text, None
        except requests.exceptions.HTTPError:
            status = response.status_code
            if status == 429 and attempt < retries:
                time.sleep(retry_delay * attempt)
                continue
            return None, f"Gemini API Error {status}"
        except Exception as e:
            return None, f"Gemini error: {str(e)}"

    return None, "Gemini rate limit — moving to fallback."


def call_groq(prompt, max_tokens=1500, retries=2, retry_delay=10):
    """Calls Groq API with retry on rate limit."""
    api_key = get_groq_key()
    if not api_key:
        return None, "No Groq API key configured."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(GROQ_BASE_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            return text, None
        except requests.exceptions.HTTPError:
            status = response.status_code
            if status == 429 and attempt < retries:
                time.sleep(retry_delay * attempt)
                continue
            return None, f"Groq API Error {status}"
        except Exception as e:
            return None, f"Groq error: {str(e)}"

    return None, "Groq rate limit — moving to fallback."


def call_openrouter(prompt, max_tokens=1500, retries=2, retry_delay=10):
    """Calls OpenRouter API with retry on rate limit."""
    api_key = get_openrouter_key()
    if not api_key:
        return None, "No OpenRouter API key configured."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://pamojadata.streamlit.app",
        "X-Title": "PamojaData"
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            return text, None
        except requests.exceptions.HTTPError:
            status = response.status_code
            if status == 429 and attempt < retries:
                time.sleep(retry_delay * attempt)
                continue
            return None, f"OpenRouter API Error {status}"
        except Exception as e:
            return None, f"OpenRouter error: {str(e)}"

    return None, "OpenRouter rate limit exceeded."


# ── MAIN CALLER WITH FALLBACK ─────────────────────────────────────────────────

def call_ai(prompt, max_tokens=1500):
    """
    Tries Gemini first, then Groq, then OpenRouter.
    Automatically falls back if one fails or hits rate limits.
    """
    errors = []

    # Try Gemini first
    if get_gemini_key():
        text, error = call_gemini(prompt, max_tokens)
        if text:
            return text
        errors.append(f"Gemini: {error}")
        st.warning(f"⚠️ Gemini unavailable ({error}). Trying Groq...")

    # Try Groq second
    if get_groq_key():
        text, error = call_groq(prompt, max_tokens)
        if text:
            return text
        errors.append(f"Groq: {error}")
        st.warning(f"⚠️ Groq unavailable ({error}). Trying OpenRouter...")

    # Try OpenRouter third
    if get_openrouter_key():
        text, error = call_openrouter(prompt, max_tokens)
        if text:
            return text
        errors.append(f"OpenRouter: {error}")

    # All failed
    error_summary = " | ".join(errors)
    return f"⚠️ All AI providers failed: {error_summary}\n\nPlease check your API keys in .streamlit/secrets.toml and try again."


# ── PROMPT BUILDER ────────────────────────────────────────────────────────────

def build_prompt(analyzed_df, sector_summary, overall_summary,
                 donor_type, qualitative_notes, org_name, report_period,
                 risk_summary=None):
    """Builds an optimized concise prompt to reduce token usage."""
    donor_guideline = DONOR_GUIDELINES.get(donor_type, DONOR_GUIDELINES["General"])
    top_indicators = analyzed_df.head(10).to_string(index=False)
    sector_text = sector_summary.to_string(index=False)

    risk_section = ""
    if risk_summary:
        risk_section = f"\nRisk: High={risk_summary['high_risk']} Medium={risk_summary['medium_risk']} Low={risk_summary['low_risk']}"

    qualitative_section = ""
    if qualitative_notes and qualitative_notes.strip():
        qualitative_section = f"\nField Notes: {qualitative_notes[:500]}"

    return f"""Senior M&E specialist writing donor report for {org_name}.
Period: {report_period or 'Current Period'} | Donor: {donor_type}
Guidelines: {donor_guideline}

Performance: {overall_summary['overall_achievement']}% overall | {overall_summary['met']} met | {overall_summary['on_track']} on track | {overall_summary['off_track']} off track
Beneficiaries: {int(overall_summary['total_achieved']):,} reached of {int(overall_summary['total_target']):,} targeted
{risk_section}{qualitative_section}

Top Indicators:
{top_indicators}

Sectors:
{sector_text}

Write a professional donor narrative with these sections:
## 1. Executive Summary
## 2. Key Achievements
## 3. Challenges & Mitigation
## 4. Recommendations & Next Steps
## 5. Conclusion

Professional tone, full paragraphs, no bullet points."""


# ── PUBLIC FUNCTIONS ──────────────────────────────────────────────────────────

def generate_narrative(analyzed_df, sector_summary, overall_summary,
                       donor_type="General", qualitative_notes="",
                       org_name="Our Organisation", report_period="",
                       risk_summary=None):
    """Generates full donor narrative using available AI provider."""
    prompt = build_prompt(
        analyzed_df, sector_summary, overall_summary,
        donor_type, qualitative_notes, org_name, report_period,
        risk_summary
    )
    return call_ai(prompt, max_tokens=1500)


def generate_executive_brief(overall_summary, sector_summary,
                              org_name, report_period, donor_type):
    """Generates a short executive brief for senior leadership."""
    sector_text = sector_summary.to_string(index=False)
    prompt = f"""Executive brief for {org_name} | Period: {report_period} | Donor: {donor_type}

Performance: {overall_summary['overall_achievement']}% | Met: {overall_summary['met']}/{overall_summary['total_indicators']} | Off Track: {overall_summary['off_track']}

Sectors:
{sector_text}

Write 3 short paragraphs: headline performance, key wins/concerns, immediate actions.
Sharp, direct, leadership-ready. No headers."""

    return call_ai(prompt, max_tokens=400)