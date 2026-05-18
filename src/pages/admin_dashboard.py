"""
Admin Dashboard Page
Provides comprehensive admin controls for user management, system monitoring, and security.
"""

import streamlit as st
from datetime import datetime, timedelta
from src.auth.auth import (
    has_permission, get_all_users, create_admin_invite,
    get_admin_invites, revoke_admin_invite, get_recent_audit_logs
)
from src.auth.admin_management import (
    get_all_users_with_roles, search_users, suspend_user, unsuspend_user,
    ban_user, unban_user, delete_user, get_user_activity, get_login_history,
    get_system_statistics, get_recent_activity, get_failed_login_attempts
)


def render_admin_dashboard():
    """Render the admin dashboard."""
    
    # Check admin permission
    user = st.session_state.get('user', {})
    user_id = user.get('id')
    role = user.get('role', '')
    
    if not has_permission(role, 'user_management'):
        st.error("❌ You do not have permission to access the admin dashboard.")
        st.stop()
    
    st.markdown("""
        <div class="pamoja-hero">
            <div class="tagline">System Administration</div>
            <h1>Admin Dashboard 🛡️</h1>
            <p>Manage users, monitor system activity, and maintain security.</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Tabs for different admin functions
    tab_overview, tab_users, tab_invites, tab_activity, tab_security = st.tabs([
        "📊 Overview",
        "👥 User Management",
        "🔑 Invite Management",
        "📋 Activity Logs",
        "🔒 Security"
    ])
    
    with tab_overview:
        render_overview()
    
    with tab_users:
        render_user_management(user_id)
    
    with tab_invites:
        render_invite_management(user_id)
    
    with tab_activity:
        render_activity_logs()
    
    with tab_security:
        render_security_monitoring()


def render_overview():
    """Render system overview statistics."""
    st.markdown("### System Overview")
    
    stats = get_system_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", stats['total_users'])
    
    with col2:
        st.metric("Active Users", stats['active_users'])
    
    with col3:
        st.metric("Suspended Users", stats['suspended_users'])
    
    with col4:
        st.metric("Banned Users", stats['banned_users'])
    
    st.markdown("---")
    
    col5, col6, col7 = st.columns(3)
    
    with col5:
        st.metric("Unverified Emails", stats['unverified_users'])
    
    with col6:
        st.metric("Active Sessions", stats['active_sessions'])
    
    with col7:
        st.metric("Failed Logins (24h)", stats['failed_logins_24h'])
    
    st.markdown("---")
    st.markdown("### Role Distribution")
    
    role_dist = stats.get('role_distribution', {})
    if role_dist:
        col_labels = list(role_dist.keys())
        col_values = list(role_dist.values())
        
        import pandas as pd
        df = pd.DataFrame({
            'Role': col_labels,
            'Count': col_values
        })
        
        st.bar_chart(df.set_index('Role'))
    else:
        st.info("No role distribution data available.")


def render_user_management(admin_id: int):
    """Render user management interface."""
    st.markdown("### User Management")
    
    # Search functionality
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_query = st.text_input("🔍 Search users by name, email, or username")
    
    with col2:
        if st.button("Search", use_container_width=True):
            st.session_state['search_query'] = search_query
    
    # Get users
    if 'search_query' in st.session_state and st.session_state['search_query']:
        users = search_users(st.session_state['search_query'])
        st.info(f"Found {len(users)} user(s)")
    else:
        users = get_all_users_with_roles()
    
    if not users:
        st.warning("No users found.")
        return
    
    # Display users in a table
    import pandas as pd
    df = pd.DataFrame([{
        'ID': u['id'],
        'Username': u['username'],
        'Email': u['email'],
        'Full Name': u['full_name'],
        'Roles': u.get('roles', 'N/A'),
        'Status': '✅ Active' if u['is_active'] and not u['is_suspended'] and not u['is_banned'] else (
            '⛔ Banned' if u['is_banned'] else ('⏸️ Suspended' if u['is_suspended'] else '❌ Inactive')
        ),
        'Email Verified': '✅' if u['email_verified'] else '❌',
        'Last Login': u['last_login'] or 'Never'
    } for u in users])
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("### User Actions")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_user_id = st.number_input("Select User ID", min_value=1, step=1)
    
    with col2:
        action = st.selectbox("Action", [
            "View Details",
            "Suspend",
            "Unsuspend",
            "Ban",
            "Unban",
            "Delete"
        ])
    
    if st.button("Execute Action", use_container_width=True):
        if action == "View Details":
            render_user_details(selected_user_id)
        elif action == "Suspend":
            if suspend_user(selected_user_id, admin_id):
                st.success(f"✅ User {selected_user_id} suspended.")
                st.rerun()
        elif action == "Unsuspend":
            if unsuspend_user(selected_user_id, admin_id):
                st.success(f"✅ User {selected_user_id} unsuspended.")
                st.rerun()
        elif action == "Ban":
            if ban_user(selected_user_id, admin_id):
                st.success(f"✅ User {selected_user_id} banned.")
                st.rerun()
        elif action == "Unban":
            if unban_user(selected_user_id, admin_id):
                st.success(f"✅ User {selected_user_id} unbanned.")
                st.rerun()
        elif action == "Delete":
            if st.button("⚠️ Confirm Delete", key="confirm_delete"):
                if delete_user(selected_user_id, admin_id):
                    st.success(f"✅ User {selected_user_id} deleted.")
                    st.rerun()


def render_user_details(user_id: int):
    """Render detailed user information."""
    st.markdown(f"### User Details (ID: {user_id})")
    
    users = get_all_users_with_roles()
    user = next((u for u in users if u['id'] == user_id), None)
    
    if not user:
        st.error("User not found.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Username:** {user['username']}")
        st.write(f"**Email:** {user['email']}")
        st.write(f"**Full Name:** {user['full_name']}")
        st.write(f"**Phone:** {user['phone'] or 'N/A'}")
    
    with col2:
        st.write(f"**Roles:** {user.get('roles', 'N/A')}")
        st.write(f"**Status:** {'✅ Active' if user['is_active'] else '❌ Inactive'}")
        st.write(f"**Suspended:** {'⏸️ Yes' if user['is_suspended'] else '❌ No'}")
        st.write(f"**Banned:** {'⛔ Yes' if user['is_banned'] else '❌ No'}")
    
    st.markdown("---")
    st.markdown("### Activity History")
    
    activity = get_user_activity(user_id, limit=20)
    if activity:
        import pandas as pd
        df = pd.DataFrame([{
            'Action': a['action'],
            'Details': a['details'],
            'IP Address': a['ip_address'],
            'Timestamp': a['created_at']
        } for a in activity])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No activity recorded.")
    
    st.markdown("---")
    st.markdown("### Login History")
    
    login_history = get_login_history(user_id, limit=20)
    if login_history:
        import pandas as pd
        df = pd.DataFrame([{
            'Status': '✅ Success' if a['successful'] else '❌ Failed',
            'Identifier': a['identifier'],
            'IP Address': a['ip_address'],
            'Reason': a['reason'],
            'Timestamp': a['created_at']
        } for a in login_history])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No login history recorded.")


def render_invite_management(admin_id: int):
    """Render admin invite management interface."""
    st.markdown("### Create Admin Invite")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        invite_email = st.text_input("Email Address")
    
    with col2:
        invite_role = st.selectbox("Role", [
            "Admin",
            "Staff/Manager",
            "Moderator",
            "Programme Manager",
            "M&E Officer",
            "Donor"
        ])
    
    with col3:
        expire_hours = st.number_input("Expires in (hours)", min_value=1, max_value=720, value=48)
    
    if st.button("Create Invite", use_container_width=True):
        if invite_email:
            success, message, token = create_admin_invite(invite_email, invite_role, expire_hours, admin_id)
            if success:
                st.success(message)
                st.info(f"**Invite Token:** `{token}`")
            else:
                st.error(message)
        else:
            st.warning("Please enter an email address.")
    
    st.markdown("---")
    st.markdown("### Active Invites")
    
    invites = get_admin_invites()
    if invites:
        import pandas as pd
        df = pd.DataFrame([{
            'ID': i['id'],
            'Email': i['email'],
            'Role': i['role'],
            'Token': i['invite_token'][:8] + '...',
            'Expires': i['expires_at'],
            'Used': '✅' if i['used'] else '❌'
        } for i in invites])
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        invite_id = st.number_input("Invite ID to revoke", min_value=1, step=1)
        if st.button("Revoke Invite", use_container_width=True):
            if revoke_admin_invite(invite_id, admin_id):
                st.success(f"✅ Invite {invite_id} revoked.")
                st.rerun()
    else:
        st.info("No active invites.")


def render_activity_logs():
    """Render system activity logs."""
    st.markdown("### Recent Activity")
    
    limit = st.slider("Number of records to display", min_value=10, max_value=500, value=100)
    
    activity = get_recent_activity(limit)
    
    if activity:
        import pandas as pd
        df = pd.DataFrame([{
            'User ID': a['user_id'],
            'Action': a['action'],
            'Details': a['details'],
            'IP Address': a['ip_address'],
            'Timestamp': a['created_at']
        } for a in activity])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No activity recorded.")


def render_security_monitoring():
    """Render security monitoring interface."""
    st.markdown("### Security Monitoring")
    
    col1, col2 = st.columns(2)
    
    with col1:
        hours = st.slider("Failed logins in last (hours)", min_value=1, max_value=168, value=24)
    
    with col2:
        limit = st.slider("Number of records", min_value=10, max_value=200, value=50)
    
    failed_attempts = get_failed_login_attempts(hours, limit)
    
    if failed_attempts:
        import pandas as pd
        df = pd.DataFrame([{
            'Identifier': a['identifier'],
            'IP Address': a['ip_address'],
            'Reason': a['reason'],
            'Timestamp': a['created_at']
        } for a in failed_attempts])
        
        st.warning(f"⚠️ Found {len(failed_attempts)} failed login attempts in the last {hours} hour(s)")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.success(f"✅ No failed login attempts in the last {hours} hour(s)")
