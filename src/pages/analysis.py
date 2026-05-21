import streamlit as st

from src.analysis.indicator_analysis import (
    calculate_achievement, sector_summary, period_summary,
    location_summary, sector_period_trend, overall_summary,
    get_off_track, get_top_performers, get_bottom_performers
)
from src.prediction.risk_predictor import (
    predict_risk, get_risk_summary, train_model
)
from src.visualization.charts import (
    sector_bar_chart, trend_line_chart, status_donut_chart,
    location_bar_chart, risk_gauge, sector_chart_for_export
)
from src.reporting.ai_reporter import generate_narrative, generate_executive_brief
from src.reporting.report_export import create_word_report
from src.database.db import save_report


def render_analysis():
    st.markdown('<div class="section-title">Indicator Analysis</div>', unsafe_allow_html=True)

    if 'df' not in st.session_state:
        st.warning("⚠️ Load your data first.")
        st.stop()

    df = st.session_state['df']
    mapping = st.session_state['mapping']

    analyzed = calculate_achievement(df, mapping)
    sec_sum = sector_summary(analyzed, mapping)
    per_sum = period_summary(analyzed, mapping)
    loc_sum = location_summary(analyzed, mapping)
    trend = sector_period_trend(analyzed, mapping)
    overall = overall_summary(analyzed, mapping)

    st.session_state.update({
        'analyzed_df': analyzed,
        'sector_summary': sec_sum,
        'period_summary': per_sum,
        'location_summary': loc_sum,
        'trend_df': trend,
        'overall_summary': overall
    })

    c1, c2, c3, c4, c5 = st.columns(5)
    cards = [
        (c1, f"{overall['overall_achievement']}%", "Overall Achievement", "teal"),
        (c2, overall['total_indicators'], "Total Indicators", ""),
        (c3, overall['met'], "Met / Exceeded", "green"),
        (c4, overall['on_track'], "On Track", "orange"),
        (c5, overall['off_track'], "Off Track", "red"),
    ]
    for col, val, label, color in cards:
        with col:
            st.markdown(f"""<div class="metric-card {color}">
                <div class="value">{val}</div>
                <div class="label">{label}</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 All Indicators", "🔴 Off Track", "🏭 By Sector", "📍 By Location", "📈 Trends"])

    with tab1:
        st.dataframe(analyzed[[mapping['indicator_name'], mapping['sector'], mapping['target'], mapping['achieved'], 'Variance', '% Achievement', 'Status']], use_container_width=True)
    with tab2:
        off = get_off_track(analyzed)
        if not off.empty:
            st.error(f"🔴 {len(off)} indicator(s) need attention")
            st.dataframe(off[[mapping['indicator_name'], mapping['sector'], mapping['target'], mapping['achieved'], '% Achievement', 'Status']], use_container_width=True)
        else:
            st.success("🎉 All indicators on track!")
    with tab3:
        st.dataframe(sec_sum, use_container_width=True)
    with tab4:
        if loc_sum is not None:
            st.dataframe(loc_sum, use_container_width=True)
        else:
            st.info("No location column mapped.")
    with tab5:
        if trend is not None:
            st.dataframe(trend, use_container_width=True)
        else:
            st.info("Trend analysis needs multi-period data.")

    st.success("✅ Analysis complete! Proceed to Risk Prediction or Dashboard →")


def render_risk_prediction():
    st.markdown('<div class="section-title">Risk Prediction Engine</div>', unsafe_allow_html=True)

    if 'analyzed_df' not in st.session_state:
        st.warning("⚠️ Complete the Analysis step first.")
        st.stop()

    analyzed = st.session_state['analyzed_df']
    mapping = st.session_state['mapping']

    st.info("🤖 Uses Random Forest ML to identify indicators at risk of going off track. Falls back to rule-based scoring if insufficient training data.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏋️ Train ML Model", use_container_width=True):
            with st.spinner("Training Random Forest model..."):
                result = train_model(analyzed, mapping)
            if 'error' in result:
                st.warning(f"⚠️ {result['error']}")
            else:
                st.success(f"✅ Model trained! Accuracy: {result['accuracy']}%")
    with col2:
        if st.button("🔮 Run Risk Prediction", use_container_width=True):
            with st.spinner("Predicting risk levels..."):
                risk_df = predict_risk(analyzed, mapping)
                risk_sum = get_risk_summary(risk_df)
                st.session_state['risk_df'] = risk_df
                st.session_state['risk_summary'] = risk_sum

    if 'risk_df' in st.session_state:
        risk_df = st.session_state['risk_df']
        risk_sum = st.session_state['risk_summary']

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class="metric-card red"><div class="value">{risk_sum['high_risk']}</div><div class="label">High Risk</div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="metric-card orange"><div class="value">{risk_sum['medium_risk']}</div><div class="label">Medium Risk</div></div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="metric-card green"><div class="value">{risk_sum['low_risk']}</div><div class="label">Low Risk</div></div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.dataframe(risk_df, use_container_width=True)
        st.caption(f"Prediction method: {risk_df['prediction_method'].iloc[0]}")


def render_dashboard():
    st.markdown('<div class="section-title">Programme Dashboard</div>', unsafe_allow_html=True)

    if 'analyzed_df' not in st.session_state:
        st.warning("⚠️ Complete the Analysis step first.")
        st.stop()

    analyzed = st.session_state['analyzed_df']
    sec_sum = st.session_state['sector_summary']
    overall = st.session_state['overall_summary']
    mapping = st.session_state['mapping']

    c1, c2 = st.columns([1, 2])
    with c1:
        st.plotly_chart(status_donut_chart(overall), use_container_width=True)
    with c2:
        st.plotly_chart(sector_bar_chart(sec_sum, mapping['sector']), use_container_width=True)

    if st.session_state.get('trend_df') is not None:
        st.plotly_chart(trend_line_chart(st.session_state['trend_df'], mapping['period'], mapping['sector']), use_container_width=True)

    if st.session_state.get('location_summary') is not None:
        st.plotly_chart(location_bar_chart(st.session_state['location_summary'], mapping['location']), use_container_width=True)

    if st.session_state.get('risk_summary'):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.plotly_chart(risk_gauge(st.session_state['risk_summary']), use_container_width=True)
        with c2:
            st.markdown("**Top Performers**")
            st.dataframe(get_top_performers(analyzed, mapping), use_container_width=True)

    st.markdown("---")
    st.markdown("**Bottom Performers — Need Attention**")
    st.dataframe(get_bottom_performers(analyzed, mapping), use_container_width=True)


def render_ai_report():
    st.markdown('<div class="section-title">AI Report Generator</div>', unsafe_allow_html=True)

    if 'analyzed_df' not in st.session_state:
        st.warning("⚠️ Complete the Analysis step first.")
        st.stop()

    analyzed = st.session_state['analyzed_df']
    sec_sum = st.session_state['sector_summary']
    overall = st.session_state['overall_summary']
    mapping = st.session_state['mapping']
    donor_type = st.session_state.get('donor_type', 'General')
    org_name = st.session_state.get('org_name', 'Our Organisation')
    report_period = st.session_state.get('report_period', '')

    qualitative_notes = st.text_area("Field Notes & Qualitative Context (recommended)", placeholder="Add context: success stories, operational challenges, community feedback...", height=120)
    report_type = st.radio("Report Type", ["📄 Full Donor Report", "📋 Executive Brief"], horizontal=True)

    if st.button("🤖 Generate with Gemini AI", use_container_width=True):
        with st.spinner("Gemini AI is writing your report..."):
            risk_summary = st.session_state.get('risk_summary', None)
            if report_type == "📄 Full Donor Report":
                narrative = generate_narrative(analyzed, sec_sum, overall, donor_type=donor_type, qualitative_notes=qualitative_notes, org_name=org_name, report_period=report_period, risk_summary=risk_summary)
            else:
                narrative = generate_executive_brief(overall, sec_sum, org_name, report_period, donor_type)
            if isinstance(narrative, str) and narrative.startswith("⚠️"):
                st.error(narrative)
            else:
                st.session_state['narrative'] = narrative
                save_report(report_period=report_period, donor_type=donor_type, narrative=narrative)
                st.success("✅ Report generated!")

    if 'narrative' in st.session_state:
        st.markdown("---")
        edited = st.text_area("Review & Edit Narrative", value=st.session_state['narrative'], height=500, label_visibility="visible")
        st.session_state['narrative'] = edited

        st.markdown("---")
        if st.button("📄 Download Word Report", use_container_width=True):
            with st.spinner("Assembling Word document..."):
                chart_buf = sector_chart_for_export(sec_sum, mapping['sector'])
                doc_io = create_word_report(
                    analyzed_df=analyzed,
                    sector_summary=sec_sum,
                    narrative=st.session_state['narrative'],
                    mapping=mapping,
                    org_name=org_name,
                    report_period=report_period,
                    chart_buf=chart_buf,
                    trend_df=st.session_state.get('trend_df'),
                    disagg_df=st.session_state.get('location_summary'),
                    logo=st.session_state.get('logo')
                )
            st.download_button(
                label="⬇️ Download .docx",
                data=doc_io,
                file_name=f"PamojaData_{org_name.replace(' ','_')}_{report_period.replace(' ','_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )