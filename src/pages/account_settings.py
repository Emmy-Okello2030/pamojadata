"""
Account Settings Page
Allows users to manage their profile and account security.
"""

import streamlit as st
from src.auth.auth import (
    get_user_profile, update_user_profile, change_password,
    validate_password_strength, get_user_roles_by_id, get_role_description
)
from src.auth.auth_enhanced import get_password_strength_score


def render_account_settings():
    """Render the account settings page."""
    
    user = st.session_state.get('user', {})
    user_id = user.get('id')
    
    if not user_id:
        st.error("❌ You must be logged in to access account settings.")
        st.stop()
    
    st.markdown("""
        <div class="pamoja-hero">
            <div class="tagline">User Account</div>
            <h1>Account Settings ⚙️</h1>
            <p>Manage your profile, security, and preferences.</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Tabs for different settings
    tab_profile, tab_security, tab_roles = st.tabs([
        "👤 Profile",
        "🔐 Security",
        "🔑 Roles & Permissions"
    ])
    
    with tab_profile:
        render_profile_settings(user_id)
    
    with tab_security:
        render_security_settings(user_id)
    
    with tab_roles:
        render_roles_settings(user_id)


def render_profile_settings(user_id: int):
    """Render profile management interface."""
    st.markdown("### Profile Information")
    
    profile = get_user_profile(user_id)
    
    if not profile:
        st.error("Unable to load profile.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Username:** {profile['username']}")
        st.write(f"**Email:** {profile['email']}")
        st.write(f"**Email Verified:** {'✅ Yes' if profile['email_verified'] else '❌ No'}")
    
    with col2:
        st.write(f"**Created:** {profile['created_at']}")
        st.write(f"**Last Login:** {profile['last_login'] or 'Never'}")
        st.write(f"**Account Status:** {'✅ Active' if profile['is_active'] else '❌ Inactive'}")
    
    st.markdown("---")
    st.markdown("### Update Profile")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_full_name = st.text_input(
            "Full Name",
            value=profile['full_name'],
            placeholder="Enter your full name"
        )
    
    with col2:
        new_phone = st.text_input(
            "Phone (optional)",
            value=profile['phone'] or "",
            placeholder="Enter your phone number"
        )
    
    if st.button("Update Profile", use_container_width=True):
        success, message = update_user_profile(user_id, new_full_name, new_phone)
        if success:
            st.success(message)
            st.session_state['user']['full_name'] = new_full_name
            st.rerun()
        else:
            st.error(message)


def render_security_settings(user_id: int):
    """Render security management interface."""
    st.markdown("### Change Password")
    
    col1, col2 = st.columns(2)
    
    with col1:
        current_password = st.text_input(
            "Current Password",
            type="password",
            placeholder="Enter your current password"
        )
    
    with col2:
        st.empty()
    
    st.markdown("---")
    
    new_password = st.text_input(
        "New Password",
        type="password",
        placeholder="Enter a strong password"
    )
    
    if new_password:
        strength_score = get_password_strength_score(new_password)
        strength_label = "Weak 🔴" if strength_score < 40 else (
            "Fair 🟡" if strength_score < 70 else "Strong 🟢"
        )
        st.progress(strength_score / 100, text=f"Password Strength: {strength_label}")
    
    confirm_password = st.text_input(
        "Confirm New Password",
        type="password",
        placeholder="Confirm your new password"
    )
    
    if st.button("Change Password", use_container_width=True):
        if not current_password:
            st.warning("Please enter your current password.")
        elif not new_password:
            st.warning("Please enter a new password.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        else:
            success, message = change_password(user_id, current_password, new_password)
            if success:
                st.success(message)
            else:
                st.error(message)
    
    st.markdown("---")
    st.markdown("### Password Requirements")
    
    st.info("""
    Your password must:
    - Be at least 12 characters long
    - Contain uppercase and lowercase letters
    - Contain at least one number
    - Contain at least one special character (!@#$%^&*-_=+[]{}|;:,<.>/?)
    - Not contain common patterns
    """)


def render_roles_settings(user_id: int):
    """Render roles and permissions information."""
    st.markdown("### Your Roles & Permissions")
    
    roles = get_user_roles_by_id(user_id)
    
    if not roles:
        st.warning("No roles assigned.")
        return
    
    for role in roles:
        with st.expander(f"🔑 {role}", expanded=True):
            description = get_role_description(role)
            st.write(f"**Description:** {description}")
            
            # Display permissions for this role
            from src.auth.auth import ROLE_PERMISSIONS
            permissions = ROLE_PERMISSIONS.get(role, [])
            
            if permissions:
                st.write("**Permissions:**")
                for perm in permissions:
                    st.write(f"- ✅ {perm}")
            else:
                st.write("No permissions assigned.")
