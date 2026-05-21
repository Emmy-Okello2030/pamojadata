import streamlit as st
import pandas as pd
import json
from src.reporting.ai_reporter import call_gemini, call_groq, call_openrouter

class AIQualityChecker:
    def analyze_quality(self, df, mapping, ai_choice="all", refresh=False):
        # 1. Prepare a summary of the data for the AI
        data_sample = df.head(10).to_string()
        prompt = f"""Analyze the quality of this humanitarian data. 
        Mapping: {mapping}
        Data Sample: {data_sample}
        
        Return ONLY a JSON object with:
        {{
            "quality_score": 0.0 to 1.0,
            "quality_grade": "A-F",
            "passed_checks": int,
            "failed_checks": int,
            "recommendations": ["list of strings"]
        }}"""

        # 2. Check Cache
        if not refresh and f"result_{ai_choice}" in st.session_state:
            return st.session_state[f"result_{ai_choice}"]

        # 3. Call the actual AI
        with st.spinner(f"Requesting analysis from {ai_choice}..."):
            if ai_choice == "gemini":
                response, error = call_gemini(prompt)
            elif ai_choice == "grok":
                response, error = call_groq(prompt)
            else:
                # Fallback to local statistical logic if AI fails or choice is statistical
                response, error = None, "Using local logic"

        # 4. Parse Response or use Fallback
        if response:
            try:
                # Try to extract JSON from the AI response
                start = response.find("{")
                end = response.rfind("}") + 1
                results = json.loads(response[start:end])
            except:
                results = self._fallback_logic(df)
        else:
            results = self._fallback_logic(df)

        st.session_state[f"result_{ai_choice}"] = results
        return results

    def _fallback_logic(self, df):
        """Local logic if AI is unavailable"""
        missing = df.isna().sum().sum()
        score = max(0.1, 1.0 - (missing / (df.size + 1)))
        return {
            "quality_score": score,
            "quality_grade": "A" if score > 0.9 else "B" if score > 0.8 else "C",
            "passed_checks": 5,
            "failed_checks": 1 if missing > 0 else 0,
            "recommendations": ["Ensure all critical fields are filled."] if missing > 0 else ["Data looks good."]
        }

def get_ai_quality_checker():
    return AIQualityChecker()
