import streamlit as st
from src.pages.quality_monitor import render_quality_monitor
from src.auth.auth import has_permission, require_permission
from src.pages import (
    render_home,
    render_data_input,
    render_data_quality,
    render_analysis,
    render_risk_prediction,
    render_dashboard,
    render_ai_report,
    render_logframe_builder,
    render_data_responsibility,
    render_user_management,
    render_hdx_data,
    render_three_w_tracking,
    render_budget_tracking,
    render_settings,
)

PAGE_RENDERERS = {
    "🏠 Home": render_home,
    "📁 Data Input": render_data_input,
    "🔍 Data Quality": render_data_quality,
    "📈 Analysis": render_analysis,
    "🔮 Risk Prediction": render_risk_prediction,
    "📊 Dashboard": render_dashboard,
    "✍️ AI Report": render_ai_report,
    "📐 Logframe Builder": render_logframe_builder,
    "🛡️ Data Responsibility": render_data_responsibility,
    "👥 User Management": render_user_management,
    "🌐 HDX Data": render_hdx_data,
    "📍 3W Tracking": render_three_w_tracking,
    "💰 Budget Tracking": render_budget_tracking,
    "⚙️ Settings": render_settings,
}

PAGE_PERMISSIONS = {
    "🏠 Home": None,
    "📁 Data Input": "data_input",
    "🔍 Data Quality": "data_quality",
    "📈 Analysis": "analysis",
    "🔮 Risk Prediction": "risk_prediction",
    "📊 Dashboard": "dashboard",
    "✍️ AI Report": "ai_report",
    "📐 Logframe Builder": "logframe",
    "🛡️ Data Responsibility": "data_responsibility",
    "👥 User Management": "user_management",
    "🌐 HDX Data": "hdx",
    "📍 3W Tracking": "three_w",
    "💰 Budget Tracking": "budget",
    "⚙️ Settings": "settings",
}


def render_page(page_name: str):
    permission = PAGE_PERMISSIONS.get(page_name)
    role = st.session_state.get('user', {}).get('role', '')
    if permission is not None:
        try:
            require_permission(role, permission)
        except PermissionError:
            st.error("⛔ You do not have permission to access this page.")
            return

    renderer = PAGE_RENDERERS.get(page_name)
    if renderer:
        renderer()
    else:
        st.warning("Page not found. Please select a valid page from the sidebar.")

from src.pages.quality_monitor import render_quality_monitor
PAGE_RENDERERS['quality_monitor'] = render_quality_monitor
PAGE_PERMISSIONS['quality_monitor'] = 'Standard User'
