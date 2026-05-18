import streamlit as st


def render_home():
    st.markdown('<div class="section-title">Welcome</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="pamoja-hero">
        <div class="tagline">Humanitarian Intelligence Platform</div>
        <h1>PamojaData 🌍</h1>
        <p>From field collection to donor submission — automated, AI-powered, built for the development sector.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown('<div class="section-title">Platform Modules</div>', unsafe_allow_html=True)
        modules = [
            ("📁", "Data Input", "Upload CSV/Excel or connect directly to KoboToolbox"),
            ("🔍", "Data Quality", "ML-powered anomaly detection and data validation"),
            ("📈", "Analysis", "Indicator performance, sector trends, geographic breakdown"),
            ("🔮", "Risk Prediction", "Random Forest model predicts at-risk indicators early"),
            ("📊", "Dashboard", "Interactive visualizations for programme managers"),
            ("✍️", "AI Report", "Gemini AI generates donor-ready narratives in minutes"),
            ("📐", "Logframe Builder", "Build and export logical frameworks for any donor"),
            ("🛡️", "Data Responsibility", "IASC-aligned PII scanning and consent management"),
            ("👥", "User Management", "Role-based permissions for Admin, Programme Manager, M&E Officer, and Donor"),
            ("🌐", "HDX Data", "Live humanitarian datasets from UN HDX platform"),
            ("📍", "3W Tracking", "Who does What Where — operational presence mapping"),
            ("💰", "Budget Tracking", "Financial monitoring and burn rate analysis"),
        ]
        for icon, title, desc in modules:
            st.markdown(f"""
            <div class='module-card'>
                <div style='font-size:1.1rem; margin-bottom:0.4rem'><strong>{icon} {title}</strong></div>
                <div style='font-size:0.92rem; color:#555'>{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-title">Getting Started</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style='background:white; padding:1rem; border-radius:12px; box-shadow:0 2px 12px rgba(0,0,0,0.05)'>
            <p>Use the sidebar to navigate the platform. Start by loading programme data in <strong>Data Input</strong>, then validate it in <strong>Data Quality</strong>.</p>
            <p>After analysis, generate a donor-ready report or build a logframe and budget summary.</p>
            <p>Admins can manage users and settings; Programme Managers can access all operational modules; M&E Officers can focus on data entry, quality, logframe, HDX, and 3W; Donors can view dashboards and AI reports.</p>
            <p>For sensitive data, use <strong>Data Responsibility</strong> before uploading files.</p>
        </div>
        """, unsafe_allow_html=True)
