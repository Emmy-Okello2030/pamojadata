import os
import streamlit as st
from typing import Dict, Any, Optional, Union

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
</style>
"""

def add_security_headers():
    """Add security headers to prevent XSS and other attacks"""
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

# ── Initialize ────────────────────────────────────────────────────────────────
initialize_app()

# ── Session check ─────────────────────────────────────────────────────────────
if 'user' in st.session_state and not validate_session():
    st.warning("Session expired. Please sign in again.")

# ── Show login if not authenticated ───────────────────────────────────────────
if 'user' not in st.session_state:
    render_login()
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
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

    # Build page list based on role permissions
    role = st.session_state['user'].get('role', '')
    available_pages = []
    for page_name in PAGE_RENDERERS.keys():
        perm = PAGE_PERMISSIONS.get(page_name)
        if perm is None or has_permission(role, perm):
            available_pages.append(page_name)

    page = st.selectbox("NAVIGATE", available_pages, key="nav_select", label_visibility="visible")

    st.markdown("---")

    # User info
    user = st.session_state['user']
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.1); padding:0.8rem 1rem; border-radius:8px">
        <div style="font-size:0.9rem; font-weight:700">👤 {user.get('username', '')}</div>
        <div style="font-size:0.75rem; opacity:0.8">{user.get('role', '')}</div>
        <div style="font-size:0.75rem; opacity:0.7">{user.get('org_name', '') or ''}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    session_token = st.session_state.get('session_token')
    if st.button("🚪 Sign Out", use_container_width=True, key="logout_button"):
        if session_token:
            logout(str(session_token))
        clear_session_state()
        st.rerun()

    st.markdown("---")

    # Pipeline status
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

# ── Render selected page ──────────────────────────────────────────────────────
if page in PAGE_RENDERERS:
    PAGE_RENDERERS[page]()