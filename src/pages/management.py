import os
import plotly.express as px
import streamlit as st
from datetime import datetime

from src.auth.auth import (
    get_all_users, update_user_role, deactivate_user,
    activate_user, create_user, change_password,
    validate_password_strength, has_permission,
    get_role_description, create_admin_invite,
    get_admin_invites, revoke_admin_invite
)
from src.hdx.hdx_connector import (
    search_datasets, get_resource_list,
    download_resource, get_country_datasets,
    format_dataset_for_analysis, get_hdx_stats,
    FEATURED_DATASETS, AFRICAN_COUNTRIES
)
from src.three_w.three_w import (
    add_three_w_entry, get_three_w_dataframe,
    get_sector_presence, get_location_presence,
    get_organisation_summary, get_coverage_gaps,
    get_reporting_periods, export_three_w_to_word
)
from src.budget.budget import (
    add_budget_line, add_expenditure,
    get_budget_summary, get_expenditure_by_period,
    get_category_summary, get_overall_budget_kpis,
    get_all_programmes, get_budget_lines,
    export_budget_to_word
)


def render_user_management():
    st.markdown('<div class="section-title">User Management</div>', unsafe_allow_html=True)

    current_user = st.session_state.get('user', {})
    if not has_permission(current_user.get('role', ''), 'user_management'):
        st.error("⛔ Admin role required.")
        st.stop()

    tab1, tab2, tab3, tab4 = st.tabs(["👥 All Users", "➕ Add User", "🔑 Change Password", "📨 Invite"])

    with tab1:
        users = get_all_users()
        
        if not users:
            st.info("No users found.")
            return
        
        role_options = ["Admin", "Staff/Manager", "Moderator", "Programme Manager", "M&E Officer", "Standard User", "Donor"]
        
        for user in users:
            user_id = user.get('id', 0)
            username = user.get('username', 'Unknown')
            email = user.get('email', 'No email')
            org_name = user.get('org_name', 'No org')
            last_login = user.get('last_login', 'Never')
            is_active = user.get('is_active', False)
            
            current_role = user.get('role')
            if not current_role or current_role not in role_options:
                current_role = 'Standard User'
            
            status_color = "#D5F5E3" if is_active else "#FADBD8"
            
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            
            with c1:
                st.markdown(f"""<div style="background:{status_color}; padding:0.6rem 1rem; border-radius:8px; margin-bottom:0.4rem">
                    <strong>{username}</strong> <span style="font-size:0.8rem; color:#666">— {email}</span><br>
                    <span style="font-size:0.8rem">{org_name} | Last login: {last_login}</span></div>""", unsafe_allow_html=True)
            
            with c2:
                try:
                    default_index = role_options.index(current_role)
                except (ValueError, TypeError):
                    default_index = role_options.index('Standard User')
                
                new_role = st.selectbox("Role", role_options, index=default_index, key=f"role_{user_id}", label_visibility="collapsed")
                
                if new_role != current_role:
                    if st.button("Save", key=f"save_role_{user_id}"):
                        update_user_role(user_id, new_role)
                        st.rerun()
            
            with c3:
                st.markdown(f"<div style='padding:0.6rem 0; font-size:0.85rem'>{'Active' if is_active else 'Inactive'}</div>", unsafe_allow_html=True)
            
            with c4:
                if user_id != current_user.get('id'):
                    if is_active:
                        if st.button("Deactivate", key=f"deact_{user_id}"):
                            deactivate_user(user_id)
                            st.rerun()
                    else:
                        if st.button("Activate", key=f"act_{user_id}"):
                            activate_user(user_id)
                            st.rerun()

        st.markdown("---")
        st.markdown("**Role Permissions**")
        for role in ["Admin", "Staff/Manager", "Moderator", "Programme Manager", "M&E Officer", "Standard User", "Donor"]:
            st.markdown(f"""<div style="background:white; padding:0.8rem 1rem; border-radius:8px; margin-bottom:0.4rem; box-shadow:0 1px 4px rgba(0,0,0,0.06)">
                <strong>{role}</strong> — <span style="font-size:0.85rem; color:#555">{get_role_description(role)}</span></div>""", unsafe_allow_html=True)

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_org = st.text_input("Organisation")
        with c2:
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            new_role = st.selectbox("Role", ["Admin", "Staff/Manager", "Moderator", "Programme Manager", "M&E Officer", "Standard User", "Donor"])

        st.markdown(f"**Role Description:** {get_role_description(new_role)}")
        if st.button("➕ Create User", use_container_width=True):
            if not all([new_username, new_email, new_password, new_org]):
                st.warning("Please fill in all fields.")
            elif new_password != confirm_password:
                st.error("❌ Passwords do not match.")
            else:
                is_valid, message = validate_password_strength(new_password)
                if not is_valid:
                    st.error(f"❌ {message}")
                else:
                    success, msg = create_user(new_username, new_email, new_password, new_role, new_org)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    with tab3:
        old_pwd = st.text_input("Current Password", type="password")
        new_pwd = st.text_input("New Password", type="password")
        confirm_pwd = st.text_input("Confirm New Password", type="password")
        if st.button("🔑 Change Password", use_container_width=True):
            if not all([old_pwd, new_pwd, confirm_pwd]):
                st.warning("Please fill in all fields.")
            elif new_pwd != confirm_pwd:
                st.error("❌ Passwords do not match.")
            elif len(new_pwd) < 6:
                st.error("❌ Password must be at least 6 characters.")
            else:
                success, msg = change_password(current_user.get('id'), old_pwd, new_pwd)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

    with tab4:
        st.markdown('### Generate Invite Code')
        invite_email = st.text_input('Invitee Email', key='invite_email')
        invite_role = st.selectbox('Invite Role', ['Admin', 'Staff/Manager', 'Moderator', 'Programme Manager', 'M&E Officer', 'Donor'], key='invite_role')
        invite_expires = st.number_input('Expires in hours', min_value=1, max_value=168, value=48, step=1, key='invite_expires')
        if st.button('Create Invite Token', use_container_width=True, key='create_invite_token'):
            success, msg, token = create_admin_invite(invite_email, invite_role, invite_expires, current_user.get('id'))
            if success:
                st.success('Invite created successfully.')
                st.code(token, language='text')
            else:
                st.error(msg)

        st.markdown('---')
        st.markdown('#### Pending invite tokens')
        invites = get_admin_invites()
        if invites:
            for invite in invites:
                is_expired = False
                expires_at = invite.get('expires_at')
                if expires_at:
                    try:
                        if isinstance(expires_at, str):
                            expires_dt = datetime.fromisoformat(expires_at)
                        else:
                            expires_dt = expires_at
                        is_expired = expires_dt < datetime.utcnow()
                    except (ValueError, TypeError):
                        is_expired = False
                
                used = invite.get('used', False)
                if used:
                    status = 'Used'
                elif is_expired:
                    status = 'Expired'
                else:
                    status = 'Active'
                
                role_name = invite.get('role', 'Unknown')
                invite_email_addr = invite.get('email', 'No email')
                invite_token = invite.get('invite_token', 'No token')
                
                st.markdown(f"**{role_name}** invite for {invite_email_addr} — {status}")
                st.markdown(f"`{invite_token}`")
                
                # Fix: Handle None value for invite_id
                invite_id = invite.get('id')
                if invite_id is not None and not used and not is_expired:
                    if st.button(f"Revoke {invite_id}", key=f"revoke_invite_{invite_id}"):
                        if revoke_admin_invite(invite_id, current_user.get('id')):
                            st.success('Invite revoked.')
                            st.rerun()
        else:
            st.info('No invite tokens have been created yet.')


def render_hdx_data():
    st.markdown('<div class="section-title">Humanitarian Data Exchange (HDX)</div>', unsafe_allow_html=True)

    stats = get_hdx_stats()
    status_color = "#D5F5E3" if stats.get('status') == 'Connected' else "#FADBD8"
    st.markdown(f"""<div style="background:{status_color}; padding:0.8rem 1.5rem; border-radius:8px; margin-bottom:1rem">
        {'✅' if stats.get('status') == 'Connected' else '❌'} <strong>HDX Status: {stats.get('status', 'Unknown')}</strong> — {stats.get('total_datasets', 0):,} datasets available</div>""", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🔍 Search Datasets", "🌍 Browse by Country", "⭐ Featured Datasets"])

    with tab1:
        c1, c2 = st.columns([3, 1])
        with c1:
            search_query = st.text_input("Search", placeholder="e.g. food security Kenya, refugee population")
        with c2:
            country_filter = st.selectbox("Filter by Country", ["All Countries"] + list(AFRICAN_COUNTRIES.keys()))

        if st.button("🔍 Search HDX", use_container_width=True):
            with st.spinner("Searching HDX..."):
                country_code = AFRICAN_COUNTRIES.get(country_filter) if country_filter != "All Countries" else None
                results = search_datasets(search_query, rows=10, country_code=country_code)
            if isinstance(results, dict) and 'error' in results:
                st.error(f"❌ {results['error']}")
            elif not results:
                st.info("No datasets found.")
            else:
                st.success(f"✅ {len(results)} datasets found.")
                st.session_state['hdx_results'] = results

        if 'hdx_results' in st.session_state:
            for dataset in st.session_state['hdx_results']:
                with st.expander(f"📂 {dataset.get('title', 'Untitled')}"):
                    st.markdown(f"**Organisation:** {dataset.get('organization', 'Unknown')} | **Files:** {dataset.get('num_resources', 0)}")
                    if st.button("📥 Load this dataset", key=f"load_{dataset.get('id')}"):
                        with st.spinner("Fetching resources..."):
                            resources = get_resource_list(dataset.get('name'))
                        if isinstance(resources, list) and resources:
                            for r in resources:
                                if r.get('format', '').upper() in ['CSV', 'XLSX', 'XLS']:
                                    if st.button("Download", key=f"dl_{r.get('id')}"):
                                        with st.spinner("Downloading..."):
                                            df = download_resource(r.get('url'), r.get('format'))
                                        if isinstance(df, dict):
                                            st.error(df.get('error', 'Download failed'))
                                        else:
                                            st.session_state['hdx_df'] = df
                                            st.success(f"✅ {len(df)} rows loaded!")
                                            st.dataframe(df.head(), use_container_width=True)

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            country = st.selectbox("Select Country", list(AFRICAN_COUNTRIES.keys()))
        with c2:
            topic = st.selectbox("Topic", ["All", "food", "health", "displacement", "refugees", "conflict", "poverty"])

        if st.button("🌍 Browse Datasets", use_container_width=True):
            with st.spinner(f"Loading datasets for {country}..."):
                results = get_country_datasets(AFRICAN_COUNTRIES.get(country), None if topic == "All" else topic)
            if isinstance(results, list) and results:
                st.success(f"✅ {len(results)} datasets found.")
                for d in results:
                    st.markdown(f"""<div style="background:white; padding:0.8rem 1rem; border-radius:8px; margin-bottom:0.4rem; box-shadow:0 1px 4px rgba(0,0,0,0.06)">
                        <strong>📂 {d.get('title', 'Untitled')}</strong><br>
                        <span style="font-size:0.82rem; color:#666">{d.get('organization', 'Unknown')} | {d.get('num_resources', 0)} files</span></div>""", unsafe_allow_html=True)

    with tab3:
        for name, dataset_id in FEATURED_DATASETS.items():
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"""<div style="background:white; padding:0.8rem 1rem; border-radius:8px; margin-bottom:0.4rem; border-left:4px solid #1A8A7A; box-shadow:0 1px 4px rgba(0,0,0,0.06)"><strong>⭐ {name}</strong></div>""", unsafe_allow_html=True)
            with c2:
                if st.button("Load", key=f"featured_{dataset_id}"):
                    with st.spinner(f"Loading {name}..."):
                        resources = get_resource_list(dataset_id)
                    if isinstance(resources, list) and resources:
                        st.success(f"✅ {len(resources)} files found!")
                    else:
                        st.info("Dataset not available.")

    if 'hdx_df' in st.session_state:
        st.markdown("---")
        st.markdown("**Import HDX Data into Analysis**")
        hdx_df = st.session_state['hdx_df']
        cols = hdx_df.columns.tolist() if hasattr(hdx_df, 'columns') else []
        if cols:
            c1, c2, c3 = st.columns(3)
            with c1:
                ind_col = st.selectbox("Indicator Name Column", cols)
            with c2:
                val_col = st.selectbox("Value Column", cols)
            with c3:
                sector_name = st.text_input("Sector", placeholder="e.g. Protection")

            if st.button("📥 Import into PamojaData", use_container_width=True):
                formatted = format_dataset_for_analysis(hdx_df, ind_col, val_col, sector_name)
                if isinstance(formatted, dict):
                    st.error(formatted.get('error', 'Import failed'))
                else:
                    st.session_state['df'] = formatted
                    st.session_state['mapping'] = {'indicator_name': 'Indicator Name', 'sector': 'Sector', 'target': 'Target', 'achieved': 'Achieved', 'period': 'Reporting Period', 'location': None}
                    st.success("✅ HDX data imported! Go to Analysis to explore it.")


def render_three_w_tracking():
    st.markdown('<div class="section-title">3W Operational Presence Tracking</div>', unsafe_allow_html=True)
    st.info("**Who does What Where** — Map which organisations are operating where and doing what.")

    periods = get_reporting_periods()
    selected_period = st.selectbox("Filter by Reporting Period", ["All Periods"] + periods)
    filter_period = None if selected_period == "All Periods" else selected_period

    tab1, tab2, tab3, tab4 = st.tabs(["➕ Add Entry", "📊 Analysis", "📋 Full Matrix", "📄 Export"])

    with tab1:
        c1, c2, c3 = st.columns(3)
        with c1:
            org_name_3w = st.text_input("Organisation Name")
            org_type = st.selectbox("Organisation Type", ["International NGO", "Local NGO", "UN Agency", "Government", "Red Cross/Crescent", "Other"])
            sector_3w = st.selectbox("Sector", ["Food Security", "Nutrition", "Health", "WASH", "Shelter", "Protection", "Education", "Livelihoods", "Cash & Vouchers", "Other"])
            subsector = st.text_input("Subsector (optional)")
        with c2:
            activity = st.text_area("Activity Description", height=80)
            admin1 = st.text_input("Region/County/Province")
            admin2 = st.text_input("District/Sub-county")
            admin3 = st.text_input("Ward/Village (optional)")
        with c3:
            ben_targeted = st.number_input("Beneficiaries Targeted", min_value=0, value=0)
            ben_reached = st.number_input("Beneficiaries Reached", min_value=0, value=0)
            start_date = st.text_input("Start Date")
            end_date = st.text_input("End Date")
            status_3w = st.selectbox("Status", ["Active", "Planned", "Completed", "On Hold"])
            funding = st.text_input("Funding Source")
            reporting_period_3w = st.text_input("Reporting Period")

        if st.button("➕ Add 3W Entry", use_container_width=True):
            if org_name_3w and sector_3w and activity and admin1:
                add_three_w_entry(
                    organisation=org_name_3w, 
                    organisation_type=org_type, 
                    sector=sector_3w, 
                    subsector=subsector, 
                    activity=activity, 
                    admin1=admin1, 
                    admin2=admin2, 
                    admin3=admin3, 
                    location_name=admin1, 
                    latitude=0, 
                    longitude=0, 
                    beneficiaries_targeted=ben_targeted, 
                    beneficiaries_reached=ben_reached, 
                    start_date=start_date, 
                    end_date=end_date, 
                    status=status_3w, 
                    funding_source=funding, 
                    contact_name="", 
                    contact_email="", 
                    reporting_period=reporting_period_3w
                )
                st.success(f"✅ Entry added for {org_name_3w} in {admin1}!")
            else:
                st.warning("Please fill in Organisation, Sector, Activity and Location.")

    with tab2:
        df_3w = get_three_w_dataframe(filter_period)
        if df_3w.empty:
            st.info("No 3W data yet.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f"""<div class="metric-card teal"><div class="value">{df_3w['organisation'].nunique()}</div><div class="label">Organisations</div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="metric-card"><div class="value">{df_3w['sector'].nunique()}</div><div class="label">Sectors</div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class="metric-card green"><div class="value">{df_3w['admin1'].nunique()}</div><div class="label">Locations</div></div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f"""<div class="metric-card orange"><div class="value">{df_3w['beneficiaries_reached'].sum():,}</div><div class="label">Beneficiaries Reached</div></div>""", unsafe_allow_html=True)

            st.markdown("---")
            it1, it2, it3, it4 = st.tabs(["🏭 By Sector", "📍 By Location", "🏢 By Organisation", "⚠️ Coverage Gaps"])
            with it1:
                sec_pres = get_sector_presence(filter_period)
                if not sec_pres.empty:
                    st.dataframe(sec_pres, use_container_width=True)
            with it2:
                loc_pres = get_location_presence(filter_period)
                if not loc_pres.empty:
                    st.dataframe(loc_pres, use_container_width=True)
            with it3:
                org_sum = get_organisation_summary(filter_period)
                if not org_sum.empty:
                    st.dataframe(org_sum, use_container_width=True)
            with it4:
                gaps = get_coverage_gaps(filter_period)
                if not gaps.empty:
                    st.warning(f"⚠️ {len(gaps)} location(s) with coverage gaps.")
                    st.dataframe(gaps, use_container_width=True)
                else:
                    st.success("✅ No coverage gaps detected.")

    with tab3:
        df_3w = get_three_w_dataframe(filter_period)
        if df_3w.empty:
            st.info("No data yet.")
        else:
            st.dataframe(df_3w, use_container_width=True)

    with tab4:
        if st.button("📄 Generate Word Report", use_container_width=True):
            with st.spinner("Generating 3W report..."):
                buf = export_three_w_to_word(filter_period)
            st.download_button(
                label="⬇️ Download 3W Report (.docx)", 
                data=buf, 
                file_name=f"3W_Matrix_{selected_period.replace(' ', '_')}.docx", 
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                use_container_width=True
            )


def render_budget_tracking():
    st.markdown('<div class="section-title">Budget Tracking</div>', unsafe_allow_html=True)
    st.info("Monitor programme budget utilisation alongside indicator performance.")

    programmes = get_all_programmes()
    selected_programme = st.selectbox("Filter by Programme", ["All Programmes"] + programmes)
    filter_programme = None if selected_programme == "All Programmes" else selected_programme

    tab1, tab2, tab3, tab4 = st.tabs(["➕ Add Budget Line", "💸 Record Expenditure", "📊 Analysis", "📄 Export"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            prog_name = st.text_input("Programme Name")
            donor_name = st.text_input("Donor")
            budget_line = st.text_input("Budget Line")
            category = st.selectbox("Category", ["Staff Costs", "Training & Capacity Building", "Equipment & Supplies", "Travel & Transport", "Consultancy", "Community Activities", "Monitoring & Evaluation", "Overheads", "Other"])
        with c2:
            currency = st.selectbox("Currency", ["USD", "KES", "UGX", "ETB", "EUR", "GBP"])
            total_budget = st.number_input("Total Budget", min_value=0.0, value=0.0)
            q1 = st.number_input("Q1 Budget", min_value=0.0, value=0.0)
            q2 = st.number_input("Q2 Budget", min_value=0.0, value=0.0)
            q3 = st.number_input("Q3 Budget", min_value=0.0, value=0.0)
            q4 = st.number_input("Q4 Budget", min_value=0.0, value=0.0)

        if st.button("➕ Add Budget Line", use_container_width=True):
            if prog_name and budget_line and total_budget > 0:
                add_budget_line(
                    programme_name=prog_name, 
                    donor=donor_name, 
                    budget_line=budget_line, 
                    category=category, 
                    total_budget=total_budget, 
                    q1_budget=q1, 
                    q2_budget=q2, 
                    q3_budget=q3, 
                    q4_budget=q4, 
                    currency=currency
                )
                st.success(f"✅ Budget line '{budget_line}' added!")
            else:
                st.warning("Please fill in Programme Name, Budget Line and Total Budget.")

    with tab2:
        budget_lines = get_budget_lines(filter_programme)
        if not budget_lines:
            st.info("No budget lines yet.")
        else:
            line_options = {f"{bl.get('budget_line', 'Unknown')} — {bl.get('programme_name', 'Unknown')}": bl.get('id') for bl in budget_lines}
            selected_line = st.selectbox("Select Budget Line", list(line_options.keys()))
            selected_line_id = line_options[selected_line]

            c1, c2 = st.columns(2)
            with c1:
                exp_amount = st.number_input("Amount", min_value=0.0, value=0.0)
                exp_description = st.text_area("Description", height=80)
                exp_period = st.text_input("Reporting Period")
            with c2:
                exp_date = st.text_input("Expenditure Date")
                exp_approved = st.text_input("Approved By")
                exp_receipt = st.text_input("Receipt/Reference No.")

            if st.button("💸 Record Expenditure", use_container_width=True):
                if exp_amount > 0:
                    add_expenditure(
                        budget_line_id=selected_line_id, 
                        amount=exp_amount, 
                        description=exp_description, 
                        reporting_period=exp_period, 
                        expenditure_date=exp_date, 
                        approved_by=exp_approved, 
                        receipt_reference=exp_receipt
                    )
                    st.success(f"✅ Expenditure of {exp_amount:,.0f} recorded!")
                else:
                    st.warning("Please enter an amount greater than 0.")

    with tab3:
        kpis = get_overall_budget_kpis(filter_programme)
        df_budget = get_budget_summary(filter_programme)

        if df_budget.empty:
            st.info("No budget data yet.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f"""<div class="metric-card teal"><div class="value">${kpis.get('total_budget', 0):,.0f}</div><div class="label">Total Budget</div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="metric-card orange"><div class="value">${kpis.get('total_spent', 0):,.0f}</div><div class="label">Total Spent</div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class="metric-card green"><div class="value">${kpis.get('total_remaining', 0):,.0f}</div><div class="label">Remaining</div></div>""", unsafe_allow_html=True)
            with c4:
                utilisation = kpis.get('overall_utilisation', 0)
                color = "red" if utilisation > 100 else "orange" if utilisation > 80 else "green"
                st.markdown(f"""<div class="metric-card {color}"><div class="value">{utilisation}%</div><div class="label">Utilisation</div></div>""", unsafe_allow_html=True)

            st.markdown("---")
            it1, it2, it3 = st.tabs(["📋 Budget Lines", "🏷️ By Category", "📈 By Period"])
            with it1:
                st.dataframe(df_budget[['programme_name', 'budget_line', 'category', 'total_budget', 'total_spent', 'Variance', 'Utilisation %', 'Status']], use_container_width=True)
                st.plotly_chart(px.bar(df_budget, x='budget_line', y=['total_budget', 'total_spent'], title='Budget vs Expenditure', barmode='group', color_discrete_map={'total_budget': '#1A3C5E', 'total_spent': '#1A8A7A'}), use_container_width=True)
            with it2:
                cat_sum = get_category_summary(filter_programme)
                if not cat_sum.empty:
                    st.dataframe(cat_sum, use_container_width=True)
                    st.plotly_chart(px.pie(cat_sum, values='Total_Spent', names='category', title='Expenditure by Category'), use_container_width=True)
            with it3:
                period_sum = get_expenditure_by_period(filter_programme)
                if not period_sum.empty:
                    st.plotly_chart(px.line(period_sum, x='reporting_period', y='total_spent', title='Expenditure Trend', markers=True), use_container_width=True)
                else:
                    st.info("No expenditure recorded yet.")

    with tab4:
        if st.button("📄 Generate Word Report", use_container_width=True):
            with st.spinner("Generating budget report..."):
                buf = export_budget_to_word(filter_programme)
            st.download_button(
                label="⬇️ Download Budget Report (.docx)", 
                data=buf, 
                file_name=f"Budget_Report_{selected_programme.replace(' ', '_')}.docx", 
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                use_container_width=True
            )


def render_settings():
    st.markdown('<div class="section-title">Settings</div>', unsafe_allow_html=True)
    st.markdown("**API Configuration**")
    st.info("PamojaData uses Google Gemini API for narrative generation. Your API key is stored securely in `.streamlit/secrets.toml`.")
    st.code("""
# .streamlit/secrets.toml
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
""", language="toml")

    st.markdown("---")
    st.markdown("**Reset Session**")
    if st.button("🗑️ Clear All Data & Start Over", type="secondary"):
        for key in list(st.session_state.keys()):
            if key != 'user':
                del st.session_state[key]
        st.success("✅ Session cleared.")

    st.markdown("---")
    st.markdown("**About PamojaData**")
    st.markdown("""
    <div style="background:white; padding:1.5rem; border-radius:12px; font-size:0.9rem; color:#444">
        <strong>PamojaData</strong> is an end-to-end humanitarian programme intelligence platform.<br>
        <strong>Built by:</strong> Emily Okello<br>
        <strong>Stack:</strong> Python · Streamlit · SQLite · Scikit-learn · Gemini API · KoboToolbox · Plotly · HDX<br>
        <strong>Modules:</strong> Data Quality · Analysis · Risk Prediction · AI Reporting · Logframe Builder · Data Responsibility · User Auth · HDX Integration · 3W Tracking · Budget Tracking
    </div>
    """, unsafe_allow_html=True)