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
            st.warning(
                """
⚠️ **Data Responsibility Reminder**
Before uploading, confirm that:
- This file contains **no beneficiary names, IDs, phone numbers or GPS coordinates**
- Data was collected with **informed consent**
- You have removed or anonymised all personal identifiers

Go to **🛡️ Data Responsibility** in the sidebar to run a full PII scan first.
"""
            )

            limit_size = st.secrets.get("app", {}).get("max_file_size_mb", 10)
            limit_rows = st.secrets.get("app", {}).get("max_rows", 200000)
            st.info(f"Upload limits: file size ≤ {limit_size} MB; rows ≤ {limit_rows}. Upload aggregated data when possible.")

            try:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded.name)[1])
                tmp.write(uploaded.getbuffer())
                tmp.flush()
                tmp.close()

                preview_rows = 1000
                try:
                    if uploaded.name.lower().endswith('.csv'):
                        df_preview = pd.read_csv(tmp.name, nrows=preview_rows)
                    else:
                        df_preview = pd.read_excel(tmp.name, nrows=preview_rows)
                except Exception:
                    st.error("❌ Failed to parse file for preview. Check file format.")
                    os.unlink(tmp.name)
                    st.stop()

                st.markdown(f"**Preview** — showing first {len(df_preview)} rows")
                st.dataframe(df_preview.head(), use_container_width=True)

                pii_flags = scan_for_pii(df_preview)
                if pii_flags:
                    st.warning(f"⚠️ Potential PII detected in {len(pii_flags)} column(s). Review before loading.")
                    for f in pii_flags:
                        st.markdown(f"- **{f['column']}** — {f['risk_level']}: {f['recommendation']}")
                    st.markdown("---")
                else:
                    st.success("✅ No likely PII column names detected in preview (column-name scan).")

                consent_items = get_consent_checklist()
                st.markdown("**Consent checklist**")
                for item in consent_items:
                    st.markdown(f"- {item}")
                consent_confirmed = st.checkbox("I confirm the checklist above and that this file is anonymised where necessary.")

                st.markdown("---")
                st.markdown("**Column Mapping**")
                cols = df_preview.columns.tolist()
                c1, c2, c3 = st.columns(3)
                with c1:
                    ind = st.selectbox("Indicator Name", cols)
                    sec = st.selectbox("Sector", cols)
                with c2:
                    tgt = st.selectbox("Target", cols)
                    ach = st.selectbox("Achieved", cols)
                with c3:
                    per = st.selectbox("Reporting Period", cols)
                    loc = st.selectbox("Location (optional)", ["None"] + cols)

                mapping = {
                    'indicator_name': ind, 'sector': sec,
                    'target': tgt, 'achieved': ach,
                    'period': per,
                    'location': None if loc == "None" else loc
                }

                st.session_state['_uploaded_temp_path'] = tmp.name
                st.session_state['_uploaded_filename'] = uploaded.name
                st.session_state['mapping'] = mapping

                if st.button("✅ Confirm & Load Data"):
                    max_rows = st.secrets.get("app", {}).get("max_rows", 200000)
                    chunk_size = 20000
                    try:
                        if uploaded.name.lower().endswith('.csv'):
                            reader = pd.read_csv(tmp.name, chunksize=chunk_size)
                            parts = []
                            total = 0
                            for part in reader:
                                total += len(part)
                                parts.append(part)
                                if total > max_rows:
                                    st.error(f"⛔ File has too many rows ({total}). Maximum allowed is {max_rows}.")
                                    os.unlink(tmp.name)
                                    st.stop()
                            df_full = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
                        else:
                            df_full = pd.read_excel(tmp.name)
                            if len(df_full) > max_rows:
                                st.error(f"⛔ File has too many rows ({len(df_full)}). Maximum allowed is {max_rows}.")
                                os.unlink(tmp.name)
                                st.stop()

                        st.session_state['df'] = df_full
                        st.session_state['mapping'] = mapping
                        st.success(f"✅ {len(df_full)} rows loaded. Proceed to Data Quality →")

                        st.session_state['pii_deep_scan_status'] = 'running'
                        with st.spinner('Running a deep PII scan on the loaded dataset...'):
                            pii_results = deep_scan_dataframe(df_full, sample_n=1000)
                            st.session_state['pii_deep_scan'] = pii_results
                            st.session_state['pii_deep_scan_status'] = 'completed'
                    except Exception as e:
                        st.error(f"❌ Failed to process file: {str(e)}")
                    finally:
                        if os.path.exists(tmp.name):
                            os.unlink(tmp.name)

            except Exception as e:
                st.error(f"❌ Upload failed: {str(e)}")

        if 'pii_deep_scan_status' in st.session_state:
            status = st.session_state.get('pii_deep_scan_status')
            with st.expander('PII Deep Scan'):
                if status == 'running':
                    st.info('Deep PII scan is running in the background. Results will appear here when complete.')
                elif isinstance(status, str) and status.startswith('error'):
                    st.error(f'Deep scan error: {status}')
                elif status == 'completed':
                    flags = st.session_state.get('pii_deep_scan', [])
                    if not flags:
                        st.success('Deep scan completed — no likely PII found in sampled values.')
                    else:
                        st.warning(f'Deep scan completed — {len(flags)} potential issues found:')
                        for f in flags:
                            st.markdown(f"- **{f.get('column')}** ({f.get('type')}) — {f.get('risk_level')}: {f.get('recommendation')}")

                    if st.button('Clear deep-scan results'):
                        st.session_state.pop('pii_deep_scan_status', None)
                        st.session_state.pop('pii_deep_scan', None)

    elif input_method == "🔗 Connect KoboToolbox":
        st.markdown("Connect directly to your KoboToolbox account to pull live field data.")
        api_token = st.text_input("KoboToolbox API Token", type="password")
        server = st.radio("Server", ["Standard (kf.kobotoolbox.org)", "Humanitarian (kobo.humanitarianresponse.info)"], horizontal=True)
        humanitarian = "Humanitarian" in server

        if st.button("🔌 Test Connection"):
            if api_token:
                with st.spinner("Testing connection..."):
                    connected = test_connection(api_token, humanitarian)
                if connected:
                    st.success("✅ Connected to KoboToolbox!")
                    st.session_state['kobo_token'] = api_token
                    st.session_state['kobo_humanitarian'] = humanitarian
                    forms = get_kobo_forms(api_token, humanitarian)
                    if isinstance(forms, list) and forms:
                        st.session_state['kobo_forms'] = forms
                else:
                    st.error("❌ Connection failed. Check your API token.")
            else:
                st.warning("Please enter your API token.")

        if 'kobo_forms' in st.session_state:
            forms = st.session_state['kobo_forms']
            form_names = [f"{f['name']} ({f['submissions']} submissions)" for f in forms]
            selected = st.selectbox("Select Form", form_names)
            selected_uid = forms[form_names.index(selected)]['uid']

            if st.button("⬇️ Pull Data from KoboToolbox"):
                with st.spinner("Downloading submissions..."):
                    df = get_form_data(st.session_state['kobo_token'], selected_uid, st.session_state['kobo_humanitarian'])
                if isinstance(df, pd.DataFrame) and not df.empty:
                    st.success(f"✅ {len(df)} submissions downloaded!")
                    st.dataframe(df.head(), use_container_width=True)
                    st.session_state['df'] = df
                else:
                    st.error("No data returned.")


def render_data_quality():
    st.markdown('<div class="section-title">Data Quality Engine</div>', unsafe_allow_html=True)

    if 'df' not in st.session_state:
        st.warning("⚠️ Load your data first in the Data Input page.")
        st.stop()

    df = st.session_state['df']
    mapping = st.session_state['mapping']

    if st.button("🔍 Run Quality Checks", use_container_width=True):
        with st.spinner("Running ML-powered quality checks..."):
            results = run_all_checks(df, mapping)
            st.session_state['quality_results'] = results

    if 'quality_results' in st.session_state:
        results = st.session_state['quality_results']

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class="metric-card {'green' if results['passed'] else 'red'}">
                <div class="value">{results['total']}</div>
                <div class="label">Issues Found</div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="metric-card red">
                <div class="value">{results['high']}</div>
                <div class="label">High Severity</div></div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="metric-card orange">
                <div class="value">{results['medium']}</div>
                <div class="label">Medium Severity</div></div>""", unsafe_allow_html=True)

        st.markdown("---")
        if results['passed']:
            st.success("🎉 All quality checks passed!")
        else:
            for issue in results['issues']:
                badge = "badge-high" if issue['severity'] == 'High' else "badge-medium"
                st.markdown(f"""
                <div style="background:white; border-radius:8px; padding:0.8rem 1rem; margin-bottom:0.5rem; box-shadow:0 1px 4px rgba(0,0,0,0.06)">
                    <span class="quality-badge {badge}">{issue['severity']}</span>
                    <strong>{issue['type']}</strong><br>
                    <span style="font-size:0.88rem; color:#555">{issue['description']}</span>
                </div>
                """, unsafe_allow_html=True)

        if st.button("🧹 Auto-Clean Data"):
            cleaned = clean_data(df, mapping)
            st.session_state['df'] = cleaned
            st.success("✅ Data cleaned successfully.")
