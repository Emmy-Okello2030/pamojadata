import pandas as pd
import streamlit as st

from src.logframe.logframe import (
    create_logframe, add_entry, get_logframe,
    get_all_logframes, delete_logframe,
    logframe_to_dataframe, export_logframe_to_word
)
from src.responsibility.data_responsibility import (
    scan_for_pii, get_consent_checklist,
    get_data_minimisation_tips, check_file_size,
    generate_responsibility_summary
)


def render_logframe_builder():
    st.markdown('<div class="section-title">Logframe Builder</div>', unsafe_allow_html=True)
    st.info("A Logical Framework (Logframe) maps your programme from Activities → Outputs → Outcomes → Goal. Build yours here and export it as a Word document.")

    tab1, tab2 = st.tabs(["➕ Create / Edit Logframe", "📋 View All Logframes"])

    with tab1:
        st.markdown("**Step 1 — Programme Details**")
        c1, c2 = st.columns(2)
        with c1:
            lf_programme = st.text_input("Programme Name", placeholder="e.g. Climate-Smart Agriculture Kenya")
            lf_org = st.text_input("Organisation", value=st.session_state.get('org_name', ''))
        with c2:
            lf_donor = st.text_input("Donor", placeholder="e.g. EU, USAID, UN Women")
            lf_start = st.text_input("Start Date", placeholder="e.g. January 2026")
            lf_end = st.text_input("End Date", placeholder="e.g. December 2028")

        if st.button("✅ Create Logframe"):
            if lf_programme:
                lf_id = create_logframe(lf_programme, lf_org, lf_donor, lf_start, lf_end)
                st.session_state['active_logframe_id'] = lf_id
                st.success(f"✅ Logframe created for **{lf_programme}**!")
            else:
                st.warning("Please enter a programme name.")

        if 'active_logframe_id' in st.session_state:
            st.markdown("---")
            st.markdown("**Step 2 — Add Logframe Entries**")

            c1, c2 = st.columns([1, 2])
            with c1:
                entry_level = st.selectbox("Level", ["Goal", "Outcome", "Output", "Activity"])
            with c2:
                entry_desc = st.text_area("Description", placeholder="Describe this Goal/Outcome/Output/Activity...", height=80)

            c1, c2, c3 = st.columns(3)
            with c1:
                entry_indicator = st.text_input("Indicator", placeholder="e.g. % farmers using new techniques")
                entry_baseline = st.number_input("Baseline", value=0.0)
            with c2:
                entry_target = st.number_input("Target", value=0.0)
                entry_mov = st.text_input("Means of Verification", placeholder="e.g. Survey reports")
            with c3:
                entry_assumptions = st.text_input("Assumptions", placeholder="e.g. Funding remains available")
                entry_responsible = st.text_input("Responsible Party", placeholder="e.g. M&E Officer")
                entry_timeline = st.text_input("Timeline", placeholder="e.g. Q1-Q2 2026")

            if st.button("➕ Add Entry", use_container_width=True):
                if entry_desc:
                    add_entry(logframe_id=st.session_state['active_logframe_id'], level=entry_level, description=entry_desc, indicator=entry_indicator, means_of_verification=entry_mov, assumptions=entry_assumptions, target=entry_target, baseline=entry_baseline, responsible_party=entry_responsible, timeline=entry_timeline)
                    st.success(f"✅ {entry_level} entry added!")
                else:
                    st.warning("Please add a description.")

            st.markdown("---")
            st.markdown("**Current Logframe Preview**")
            df = logframe_to_dataframe(st.session_state['active_logframe_id'])
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                if st.button("📄 Export Logframe to Word", use_container_width=True):
                    with st.spinner("Generating Word document..."):
                        buf = export_logframe_to_word(st.session_state['active_logframe_id'])
                    logframe_info, _ = get_logframe(st.session_state['active_logframe_id'])
                    st.download_button(label="⬇️ Download Logframe (.docx)", data=buf, file_name=f"Logframe_{logframe_info['programme_name'].replace(' ', '_')}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            else:
                st.info("No entries yet — add your first entry above.")

    with tab2:
        logframes = get_all_logframes()
        if logframes:
            for lf in logframes:
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    st.markdown(f"""<div class="module-card"><strong>{lf['programme_name']}</strong><br>
                    <span style="font-size:0.85rem; color:#666">{lf['org_name']} | {lf['donor']} | {lf['start_date']} → {lf['end_date']}</span></div>""", unsafe_allow_html=True)
                with c2:
                    if st.button("Open", key=f"open_{lf['id']}"):
                        st.session_state['active_logframe_id'] = lf['id']
                        st.success(f"Opened: {lf['programme_name']}")
                with c3:
                    if st.button("🗑️ Delete", key=f"del_{lf['id']}"):
                        delete_logframe(lf['id'])
                        st.rerun()
        else:
            st.info("No logframes yet.")


def render_data_responsibility():
    st.markdown('<div class="section-title">Data Responsibility</div>', unsafe_allow_html=True)
    st.markdown("""<div style="background:#EAF2FF; padding:1rem 1.5rem; border-radius:10px; margin-bottom:1rem">
        <strong>🌍 IASC Data Responsibility Principles</strong><br>
        <span style="font-size:0.9rem">PamojaData follows the IASC Operational Guidance on Data Responsibility in Humanitarian Action (2023).</span>
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🔍 PII Scanner", "✅ Consent Checklist", "💡 Data Minimisation"])

    with tab1:
        st.markdown("**Scan your data for Personally Identifiable Information (PII)**")
        scan_file = st.file_uploader("Upload file to scan", type=["csv", "xlsx"], key="responsibility_upload")

        if scan_file:
            size_ok, size_msg = check_file_size(scan_file)
            if not size_ok:
                st.error(f"⛔ {size_msg}")
                st.stop()

            df = pd.read_csv(scan_file) if scan_file.name.lower().endswith('.csv') else pd.read_excel(scan_file)
            pii_flags = scan_for_pii(df)
            st.session_state['pii_flags'] = pii_flags

            if not pii_flags:
                st.success("🎉 No PII fields detected.")
            else:
                st.warning(f"⚠️ {len(pii_flags)} potential PII field(s) detected.")
                for flag in pii_flags:
                    color = "#FADBD8" if flag['risk_level'] == 'High' else "#FEF9E7" if flag['risk_level'] == 'Medium' else "#EAF2FF"
                    icon = "⛔" if flag['risk_level'] == 'High' else "⚠️" if flag['risk_level'] == 'Medium' else "ℹ️"
                    st.markdown(f"""<div style="background:{color}; padding:0.8rem 1rem; border-radius:8px; margin-bottom:0.5rem">
                        {icon} <strong>{flag['column']}</strong> <span style="font-size:0.8rem; color:#666">— {flag['risk_level']} Risk</span><br>
                        <span style="font-size:0.85rem">{flag['recommendation']}</span></div>""", unsafe_allow_html=True)

    with tab2:
        checklist = get_consent_checklist()
        all_checked = []
        for i, item in enumerate(checklist):
            checked = st.checkbox(item, key=f"consent_{i}")
            all_checked.append(checked)
        st.session_state['consent_checked'] = all(all_checked)
        if all(all_checked):
            st.success("✅ All data responsibility requirements confirmed.")
        else:
            st.warning(f"⚠️ {len([c for c in all_checked if not c])} item(s) remaining.")

        if 'pii_flags' in st.session_state:
            summary = generate_responsibility_summary(st.session_state['pii_flags'], st.session_state.get('consent_checked', False))
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""<div class="metric-card {'green' if summary['status'] == 'Pass' else 'red'}"><div class="value">{summary['status']}</div><div class="label">Overall Status</div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="metric-card red"><div class="value">{summary['high_risk_fields']}</div><div class="label">High Risk Fields</div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class="metric-card {'green' if summary['consent_confirmed'] else 'orange'}"><div class="value">{'Yes' if summary['consent_confirmed'] else 'No'}</div><div class="label">Consent Confirmed</div></div>""", unsafe_allow_html=True)

    with tab3:
        tips = get_data_minimisation_tips()
        for tip in tips:
            st.markdown(f"""<div style="background:white; padding:0.8rem 1rem; border-radius:8px; margin-bottom:0.4rem; border-left:4px solid #1A8A7A; box-shadow:0 1px 4px rgba(0,0,0,0.06)">💡 {tip}</div>""", unsafe_allow_html=True)
