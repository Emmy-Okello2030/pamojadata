import os
import tempfile
import pandas as pd
import streamlit as st
from src.collection.kobo_connector import test_connection, get_kobo_forms, get_form_data
from src.quality.quality_checks import run_all_checks, clean_data
from src.responsibility.data_responsibility import (
    scan_for_pii, get_consent_checklist,
    check_file_size, deep_scan_dataframe
)


def render_data_input():
    st.markdown('<div class="section-title">Data Input</div>', unsafe_allow_html=True)
    input_method = st.radio(
        "How would you like to load data?",
        ["📂 Upload CSV/Excel", "🔗 Connect KoboToolbox"],
        horizontal=True
    )
    
    if input_method == "📂 Upload CSV/Excel":
        uploaded = st.file_uploader("Upload programme data", type=["csv", "xlsx"])
        
        if uploaded:
            max_size = st.secrets.get("app", {}).get("max_file_size_mb", 10)
            if uploaded.size > max_size * 1024 * 1024:
                st.error(f"⛔ File too large. Maximum size is {max_size}MB.")
                st.stop()
            
            st.markdown("---")
            st.warning("⚠️ **Data Responsibility Reminder**: Confirm anonymisation before upload.")
            
            try:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded.name)[1])
                tmp.write(uploaded.getbuffer())
                tmp.flush()
                tmp.close()
                
                preview_rows = 1000
                if uploaded.name.lower().endswith('.csv'):
                    df_preview = pd.read_csv(tmp.name, nrows=preview_rows)
                else:
                    df_preview = pd.read_excel(tmp.name, nrows=preview_rows)
                
                # Remove duplicate columns from source
                df_preview = df_preview.loc[:, ~df_preview.columns.duplicated()]
                
                st.markdown(f"**Preview** — showing first {len(df_preview)} rows")
                st.dataframe(df_preview.head(), use_container_width=True)
                
                # Let user select column mapping
                st.markdown("**Column Mapping**")
                cols = df_preview.columns.tolist()
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    indicator_col = st.selectbox("Indicator Name", cols, index=0)
                    sector_col = st.selectbox("Sector", cols, index=min(1, len(cols)-1))
                with c2:
                    target_col = st.selectbox("Target", cols, index=min(2, len(cols)-1))
                    achieved_col = st.selectbox("Achieved", cols, index=min(3, len(cols)-1))
                with c3:
                    period_col = st.selectbox("Reporting Period", ["None"] + cols, index=0)
                    location_col = st.selectbox("Location", ["None"] + cols, index=0)
                
                mapping = {
                    'indicator_name': indicator_col,
                    'sector': sector_col,
                    'target': target_col,
                    'achieved': achieved_col,
                    'period': None if period_col == "None" else period_col,
                    'location': None if location_col == "None" else location_col
                }
                
                st.session_state['mapping'] = mapping
                
                # Load full data
                if uploaded.name.lower().endswith('.csv'):
                    df_full = pd.read_csv(tmp.name)
                else:
                    df_full = pd.read_excel(tmp.name)
                
                # Remove duplicate columns
                df_full = df_full.loc[:, ~df_full.columns.duplicated()]
                
                st.session_state['df'] = df_full
                st.success(f"✅ {len(df_full)} rows loaded. Proceed to Data Quality →")
                
                # Clean up temp file
                if os.path.exists(tmp.name):
                    os.unlink(tmp.name)
                    
            except Exception as e:
                st.error(f"❌ Upload failed: {str(e)}")


def render_data_quality():
    st.markdown('<div class="section-title">Data Quality Engine</div>', unsafe_allow_html=True)
    
    if 'df' not in st.session_state:
        st.warning("⚠️ Load your data first in the Data Input page.")
        st.stop()
    
    df = st.session_state['df']
    mapping = st.session_state.get('mapping', {})
    
    # Remove duplicate columns
    df = df.loc[:, ~df.columns.duplicated()]
    st.session_state['df'] = df
    
    st.info(f"📊 Dataset: {len(df)} rows, {len(df.columns)} columns")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        ai_choice = st.selectbox(
            "Select AI Provider",
            ["all", "gemini", "grok", "openrouter", "statistical_only"],
            help="'all' uses all available AI providers"
        )
    
    with col2:
        refresh_button = st.button("🔄 Refresh Analysis", use_container_width=True)
    
    with col3:
        run_button = st.button("🚀 Run Quality Checks", type="primary", use_container_width=True)
    
    should_run = run_button or refresh_button or 'quality_results' not in st.session_state
    
    if should_run:
        try:
            from src.quality.ai_quality_checker import get_ai_quality_checker
            checker = get_ai_quality_checker()
            
            with st.spinner(f"🤖 Analyzing data quality using {ai_choice}..."):
                results = checker.analyze_quality(df, mapping, ai_choice, refresh=refresh_button)
                st.session_state['quality_results'] = results
                
        except ImportError:
            from src.quality_engine.pamojadata_client import PamojaDataQualityClient
            client = PamojaDataQualityClient()
            results = client.check_data_quality(df, "current_data")
            st.session_state['quality_results'] = results
        except Exception as e:
            st.error(f"AI Quality Error: {e}")
            # Fallback to local checks
            results = run_all_checks(df, mapping)
            results['quality_score'] = 1 - (results.get('total', 0) / 100)
            results['quality_grade'] = 'A' if results['quality_score'] > 0.9 else 'B' if results['quality_score'] > 0.8 else 'C'
            st.session_state['quality_results'] = results
    
    if st.session_state.get('quality_results'):
        results = st.session_state['quality_results']
        
        st.markdown("---")
        st.subheader("📊 Quality Assessment Results")
        
        score = results.get('quality_score', 0)
        grade = results.get('quality_grade', 'N/A')
        passed = results.get('passed_checks', 0)
        failed = results.get('failed_checks', 0)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Quality Score", f"{score:.1%}")
        col2.metric("Quality Grade", grade)
        col3.metric("✅ Passed Checks", passed)
        col4.metric("❌ Failed Checks", failed)
        
        st.progress(score)
        
        if results.get('recommendations'):
            with st.expander("📋 Recommendations"):
                for rec in results.get('recommendations', [])[:5]:
                    st.write(f"• {rec}")
        
        if results.get('critical_issues'):
            with st.expander("🔴 Critical Issues"):
                for issue in results.get('critical_issues', [])[:5]:
                    st.error(f"• {issue}")
        
        # Auto-clean button
        if st.button("🧹 Auto-Clean Data", use_container_width=True):
            cleaned = clean_data(df, mapping)
            st.session_state['df'] = cleaned
            # Clear cache to force re-analysis
            if 'quality_results' in st.session_state:
                del st.session_state['quality_results']
            st.success("✅ Data cleaned successfully! Click 'Run Quality Checks' again to see improvements.")
            st.rerun()