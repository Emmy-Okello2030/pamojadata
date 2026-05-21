import os
import streamlit as st
from typing import Dict, Any, Optional, Union
import pandas as pd
from datetime import datetime

# ============================================================================
# EXISTING IMPORTS (Preserved)
# ============================================================================
from src.auth.auth import (
    initialise_auth_tables,
    login,
    register_user,
    request_password_reset,
    get_user_by_session_token,
    logout,
    has_permission,
    verify_email,
)
from src.database.db import initialise_database
from src.logframe.logframe import initialise_logframe_tables
from src.budget.budget import initialise_budget_tables
from src.three_w.three_w import initialise_three_w_tables
from src.page_handlers import PAGE_PERMISSIONS, PAGE_RENDERERS

# ============================================================================
# NEW: Quality Engine Imports
# ============================================================================
from src.quality.quality_checks import QualityChecker, get_quality_summary, run_all_checks
from src.quality_engine.pamojadata_client import PamojaDataQualityClient

# ============================================================================
# EXISTING CSS (Preserved)
# ============================================================================
CUSTOM_CSS = """
<style>
    .stApp { background-color: #F0F4F8; }
    .pamoja-hero {
        background: linear-gradient(135deg, #0D2137 0%, #1A3C5E 40%, #1A8A7A 100%);
        padding: 2rem 3rem; border-radius: 16px; margin-bottom: 2rem;
    }
    .pamoja-hero h1 { color: white; margin: 0; }
    .pamoja-hero p { color: rgba(255,255,255,0.8); }
    .stButton > button { background: linear-gradient(135deg, #1A3C5E, #1A8A7A); color: white !important; }
    
    .quality-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-left: 0.5rem;
    }
    .quality-A { background-color: #27ae60; color: white; }
    .quality-B { background-color: #2ecc71; color: white; }
    .quality-C { background-color: #f39c12; color: white; }
    .quality-D { background-color: #e67e22; color: white; }
    .quality-F { background-color: #e74c3c; color: white; }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        margin: 0.5rem 0;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1A3C5E;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #666;
        margin-top: 0.25rem;
    }
</style>
"""

# ============================================================================
# EXISTING FUNCTIONS (Preserved)
# ============================================================================
def add_security_headers():
    st.markdown("""
        <meta http-equiv="X-Content-Type-Options" content="nosniff">
        <meta http-equiv="X-Frame-Options" content="DENY">
        <meta http-equiv="X-XSS-Protection" content="1; mode=block">
        <meta name="referrer" content="strict-origin-when-cross-origin">
    """, unsafe_allow_html=True)

def clear_session_state() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]

def initialize_app() -> None:
    st.set_page_config(page_title="PamojaData", page_icon="🌍", layout="wide")
    add_security_headers()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    initialise_database()
    initialise_auth_tables()
    initialise_logframe_tables()
    initialise_budget_tables()
    initialise_three_w_tables()

def validate_session() -> bool:
    session_token = st.session_state.get('session_token')
    user = st.session_state.get('user')
    if not user or not session_token:
        return False
    authenticated = get_user_by_session_token(str(session_token))
    if not authenticated or authenticated.get('id') != user.get('id'):
        clear_session_state()
        return False
    st.session_state['user'] = authenticated
    return True

def render_login() -> None:
    st.markdown('<div class="pamoja-hero"><h1>PamojaData 🌍</h1><p>Humanitarian Intelligence Platform</p></div>', unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Sign In", "Sign Up"])

    with tab_login:
        identifier = st.text_input("Email or Username", key="login_identifier")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Sign In", use_container_width=True, key="login_button"):
            if identifier and password:
                success, result = login(identifier, password)
                if success and isinstance(result, dict):
                    st.session_state['user'] = result
                    st.session_state['session_token'] = str(result.get('token', ''))
                    st.rerun()
                elif isinstance(result, str):
                    st.error(result)
                else:
                    st.error("Login failed")
            else:
                st.warning("Please enter email/username and password.")

        st.markdown("---")
        st.caption("Default credentials: **admin** / **admin123**")

    with tab_register:
        full_name = st.text_input("Full Name", key="reg_full_name")
        email = st.text_input("Email", key="reg_email")
        phone = st.text_input("Phone (optional)", key="reg_phone")
        role = st.selectbox(
            "Role",
            ["Standard User", "Donor", "M&E Officer", "Programme Manager", "Staff/Manager", "Moderator", "Admin"],
            key="reg_role"
        )
        invite_code = st.text_input("Invite Token (if required)", key="reg_invite_code")
        password = st.text_input("Password", type="password", key="reg_password")
        confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
        terms = st.checkbox("I agree to the terms and conditions", key="reg_terms")

        if st.button("Create Account", use_container_width=True, key="register_button"):
            if not terms:
                st.error("Please agree to the terms and conditions")
            elif password != confirm:
                st.error("Passwords do not match")
            else:
                invite = invite_code if role != "Standard User" else None
                success, msg = register_user(
                    full_name=full_name,
                    email=email,
                    password=password,
                    confirm_password=confirm,
                    role=role,
                    phone=phone,
                    terms_agreed=terms,
                    invite_code=invite
                )
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

# ============================================================================
# QUALITY ENGINE INITIALIZATION
# ============================================================================
@st.cache_resource
def init_quality_system():
    return QualityChecker()

@st.cache_resource
def init_quality_client():
    return PamojaDataQualityClient()

# ============================================================================
# QUALITY DISPLAY FUNCTIONS
# ============================================================================
def display_quality_metrics(quality_results: Dict[str, Any], df: pd.DataFrame = None):
    if not quality_results:
        return
    
    st.markdown("### 📊 Data Quality Assessment")
    
    quality_score = quality_results.get('quality_score', 0)
    quality_grade = quality_results.get('quality_grade', 'N/A')
    passed = quality_results.get('passed', False)
    total_issues = quality_results.get('total', 0)
    high_issues = quality_results.get('high', 0)
    medium_issues = quality_results.get('medium', 0)
    low_issues = quality_results.get('low', 0)
    
    grade_class = f"quality-{quality_grade[0]}" if quality_grade else "quality-C"
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{quality_score:.1%}</div>
            <div class="metric-label">Quality Score</div>
            <span class="quality-badge {grade_class}">Grade {quality_grade}</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        status_text = "✅ PASSED" if passed else "⚠️ ISSUES"
        status_color = "#27ae60" if passed else "#e74c3c"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: {status_color}">{status_text}</div>
            <div class="metric-label">Overall Status</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_issues}</div>
            <div class="metric-label">Total Issues</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">🔴 {high_issues} | 🟡 {medium_issues} | 🟢 {low_issues}</div>
            <div class="metric-label">High / Medium / Low</div>
        </div>
        """, unsafe_allow_html=True)
    
    recommendations = quality_results.get('recommendations', [])
    if recommendations:
        with st.expander("📋 Recommendations", expanded=high_issues > 0):
            for rec in recommendations[:5]:
                st.write(f"• {rec}")
    
    issues = quality_results.get('issues', [])
    if issues:
        with st.expander("🔍 Detailed Issues", expanded=False):
            for issue in issues[:10]:
                severity = issue.get('severity', 'Medium')
                severity_icon = "🔴" if severity == "High" else "🟡" if severity == "Medium" else "🟢"
                st.write(f"{severity_icon} **{issue.get('type', 'Issue')}**: {issue.get('description', '')}")
    
    st.session_state['quality_results'] = quality_results
    st.session_state['quality_score'] = quality_score
    st.session_state['quality_grade'] = quality_grade

def display_quality_sidebar_indicator():
    if 'quality_score' in st.session_state:
        score = st.session_state['quality_score']
        grade = st.session_state.get('quality_grade', 'N/A')
        
        if score >= 0.9:
            color = "🟢"
            status = "Excellent"
        elif score >= 0.7:
            color = "🟡"
            status = "Good"
        elif score >= 0.5:
            color = "🟠"
            status = "Needs Review"
        else:
            color = "🔴"
            status = "Poor"
        
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.1); padding:0.5rem; border-radius:8px; margin-top: 1rem;">
            <div style="font-size:0.7rem; opacity:0.7">DATA QUALITY</div>
            <div style="font-size:1.2rem; font-weight:bold">{color} {status}</div>
            <div style="font-size:0.8rem">Score: {score:.1%} (Grade {grade})</div>
        </div>
        """, unsafe_allow_html=True)

def get_default_column_mapping(df: pd.DataFrame) -> Dict[str, str]:
    mapping = {}
    
    indicator_keywords = ['indicator', 'indicator_name', 'indicator name', 'indicatorname', 'kpi', 'metric']
    for col in df.columns:
        if any(keyword in col.lower() for keyword in indicator_keywords):
            mapping['indicator_name'] = col
            break
    if 'indicator_name' not in mapping:
        mapping['indicator_name'] = df.columns[0]
    
    target_keywords = ['target', 'target_value', 'target value', 'goal', 'plan', 'benchmark']
    for col in df.columns:
        if any(keyword in col.lower() for keyword in target_keywords):
            mapping['target'] = col
            break
    if 'target' not in mapping:
        mapping['target'] = 'target' if 'target' in df.columns else df.columns[1] if len(df.columns) > 1 else df.columns[0]
    
    achieved_keywords = ['achieved', 'actual', 'result', 'achievement', 'completed', 'reached']
    for col in df.columns:
        if any(keyword in col.lower() for keyword in achieved_keywords):
            mapping['achieved'] = col
            break
    if 'achieved' not in mapping and len(df.columns) > 2:
        mapping['achieved'] = df.columns[2]
    
    sector_keywords = ['sector', 'sector_name', 'sector name', 'area', 'theme', 'programme', 'project']
    for col in df.columns:
        if any(keyword in col.lower() for keyword in sector_keywords):
            mapping['sector'] = col
            break
    if 'sector' not in mapping:
        mapping['sector'] = 'sector' if 'sector' in df.columns else None
    
    period_keywords = ['period', 'date', 'quarter', 'month', 'year', 'reporting_period']
    for col in df.columns:
        if any(keyword in col.lower() for keyword in period_keywords):
            mapping['period'] = col
            break
    
    return mapping

def handle_data_upload(uploaded_file) -> Optional[pd.DataFrame]:
    if uploaded_file is None:
        return None
    
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Unsupported file format. Please upload CSV or Excel files.")
            return None
        
        st.success(f"✅ Loaded {len(df)} rows, {len(df.columns)} columns")
        
        st.session_state['raw_df'] = df.copy()
        st.session_state['df'] = df.copy()
        st.session_state['uploaded_filename'] = uploaded_file.name
        
        mapping = get_default_column_mapping(df)
        st.session_state['column_mapping'] = mapping
        
        with st.expander("📁 Detected Column Mapping", expanded=False):
            st.json(mapping)
        
        with st.spinner("🔍 Analyzing data quality..."):
            quality_checker = init_quality_system()
            quality_results = quality_checker.run_checks(df, mapping, use_engine=True)
            st.session_state['quality_results'] = quality_results
        
        display_quality_metrics(quality_results, df)
        
        return df
        
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None

# ============================================================================
# DATA UPLOAD PAGE - THIS IS WHERE YOU UPLOAD FILES
# ============================================================================
def data_upload_page():
    """Main data upload page with quality engine integration"""
    st.markdown('<div class="pamoja-hero"><h1>📊 Data Upload & Quality Check</h1><p>Upload your programme data for automatic quality assessment</p></div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['csv', 'xlsx', 'xls'],
        help="Upload CSV or Excel file with your programme data"
    )
    
    if uploaded_file is not None:
        df = handle_data_upload(uploaded_file)
        
        if df is not None:
            st.session_state['df'] = df
            st.session_state['data_loaded'] = True
            
            st.subheader("📋 Data Preview")
            st.dataframe(df.head(10))
            
            with st.expander("📊 Column Information"):
                col_info = pd.DataFrame({
                    'Column': df.columns,
                    'Type': df.dtypes.astype(str),
                    'Non-Null Count': df.count().values,
                    'Null Count': df.isna().sum().values,
                    'Unique Values': df.nunique().values
                })
                st.dataframe(col_info)

def quality_monitoring_dashboard():
    st.markdown('<div class="pamoja-hero"><h1>🔍 Quality Monitoring Dashboard</h1><p>Monitor data quality across all your datasets</p></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Engine Status")
        quality_client = init_quality_client()
        
        if quality_client.enabled:
            st.success("✅ Quality Engine Connected")
            st.caption(f"Endpoint: {quality_client.api_url}")
        else:
            st.warning("⚠️ Quality Engine Not Connected")
            if st.button("Retry Connection"):
                st.cache_resource.clear()
                st.rerun()
    
    with col2:
        st.subheader("📈 Quality History")
        if 'quality_history' in st.session_state and st.session_state.quality_history:
            history_df = pd.DataFrame(st.session_state.quality_history)
            st.line_chart(history_df.set_index('timestamp')['quality_score'])
        else:
            st.info("No quality history yet. Upload data to start tracking.")
    
    if 'df' in st.session_state and st.session_state['df'] is not None:
        st.markdown("---")
        st.subheader("📋 Current Dataset Quality")
        
        df = st.session_state['df']
        st.write(f"**Dataset:** {st.session_state.get('uploaded_filename', 'Current dataset')}")
        st.write(f"**Rows:** {len(df)} | **Columns:** {len(df.columns)}")
        
        if 'quality_results' in st.session_state:
            quality_results = st.session_state['quality_results']
            display_quality_metrics(quality_results, df)
            
            if 'quality_history' not in st.session_state:
                st.session_state.quality_history = []
            
            st.session_state.quality_history.append({
                'timestamp': datetime.now().isoformat(),
                'quality_score': quality_results.get('quality_score', 0),
                'quality_grade': quality_results.get('quality_grade', 'N/A'),
                'total_issues': quality_results.get('total', 0),
                'dataset': st.session_state.get('uploaded_filename', 'unknown')
            })
            
            if len(st.session_state.quality_history) > 50:
                st.session_state.quality_history = st.session_state.quality_history[-50:]

# ============================================================================
# REGISTER PAGES
# ============================================================================
# Add data upload page
if 'data_upload' not in PAGE_RENDERERS:
    PAGE_RENDERERS['data_upload'] = data_upload_page
    PAGE_PERMISSIONS['data_upload'] = 'Standard User'

# Add quality monitor page
if 'quality_monitor' not in PAGE_RENDERERS:
    PAGE_RENDERERS['quality_monitor'] = quality_monitoring_dashboard
    PAGE_PERMISSIONS['quality_monitor'] = 'Standard User'

# ============================================================================
# APP INITIALIZATION AND RENDERING
# ============================================================================

initialize_app()

if 'user' in st.session_state and not validate_session():
    st.warning("Session expired. Please sign in again.")

if 'user' not in st.session_state:
    render_login()
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:1rem 0'>
        <div style='font-size:1.5rem; font-weight:900; color:white'>🌍 PamojaData</div>
        <div style='font-size:0.7rem; color:#5EDDD0; letter-spacing:0.1em; text-transform:uppercase'>
            Humanitarian Intelligence Platform
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    role = st.session_state['user'].get('role', '')
    available_pages = []
    for page_name in PAGE_RENDERERS.keys():
        perm = PAGE_PERMISSIONS.get(page_name)
        if perm is None or has_permission(role, perm):
            available_pages.append(page_name)

    page = st.selectbox("NAVIGATE", available_pages, key="nav_select", label_visibility="visible")

    st.markdown("---")

    user = st.session_state['user']
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.1); padding:0.8rem 1rem; border-radius:8px">
        <div style="font-size:0.9rem; font-weight:700">👤 {user.get('username', '')}</div>
        <div style="font-size:0.75rem; opacity:0.8">{user.get('role', '')}</div>
        <div style="font-size:0.75rem; opacity:0.7">{user.get('org_name', '') or ''}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")
    
    display_quality_sidebar_indicator()
    
    st.markdown("")

    session_token = st.session_state.get('session_token')
    if st.button("🚪 Sign Out", use_container_width=True, key="logout_button"):
        if session_token:
            logout(str(session_token))
        clear_session_state()
        st.rerun()

    st.markdown("---")

    st.markdown("**PIPELINE STATUS**")
    pipeline = {
        "Data Loaded": 'df' in st.session_state,
        "Quality Checked": 'quality_results' in st.session_state,
        "Analysis Done": 'analyzed_df' in st.session_state,
        "Risk Assessed": 'risk_df' in st.session_state,
        "Narrative Ready": 'narrative' in st.session_state,
    }
    for step, done in pipeline.items():
        icon = "✅" if done else "⏳"
        st.markdown(f"<div style='font-size:0.85rem; padding:0.15rem 0; color:white'>{icon} {step}</div>",
                    unsafe_allow_html=True)

# Render selected page
if page in PAGE_RENDERERS:
    PAGE_RENDERERS[page]()