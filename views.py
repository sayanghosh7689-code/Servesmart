"""
views.py — Streamlit views for ServeSmart (login, student, technician, admin).
"""

import streamlit as st
import models as m
import ui
import chatbot


def login_view():
    st.title("🛠️ ServeSmart")
    st.caption("Campus Service Ticket System — log in with your account and password.")

    tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])

    with tab_login:
        role = st.radio("I am a:", ["Student", "Technician", "Admin"], horizontal=True, key="login_role")
        options = m.get_users_by_role(role)

        if not options:
            st.info(f"No {role} accounts exist yet.")
        else:
            user_id = st.selectbox(
                "Choose account", list(options.keys()),
                format_func=lambda k: f"{options[k]} ({k})", key="login_user_id",
            )
            password = st.text_input(
                "Password", type="password",
                help=f"Demo password for the seeded accounts: {m.DEFAULT_PASSWORD}",
                key="login_password",
            )

            if st.button("Log in", type="primary"):
                user = m.verify_login(user_id, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Incorrect password.")

    with tab_signup:
        st.subheader("Create an account")
        st.caption("Students and technicians can self-register below. Admin accounts are provisioned separately.")

        with st.form("signup_form", clear_on_submit=True):
            new_id = st.text_input(
                "Choose a user ID", key="signup_id",
                help="3-20 characters: letters, numbers, and underscores only.",
            )
            new_name = st.text_input("Full name", key="signup_name")
            new_role = st.selectbox("I am a:", m.SIGNUP_ROLES, key="signup_role")
            new_password = st.text_input("Password", type="password", key="signup_password")
            new_password_confirm = st.text_input("Confirm password", type="password", key="signup_password_confirm")
            submitted = st.form_submit_button("Sign up", type="primary")

        if submitted:
            ok, errors, user = m.create_user(new_id, new_name, new_role, new_password, new_password_confirm)
            if ok:
                st.success(f"Account created for {user['name']} ({user['id']}). Switch to the 'Log In' tab to sign in.")
            else:
                for e in errors:
                    st.error(e)


def student_view(user):
    st.title(f"🎓 Welcome, {user['name']}")

    my_tickets_all = [t for t in m.get_all_tickets() if t["studentId"] == user["id"]]
    ui.metrics_row(my_tickets_all)
    st.divider()

    tab_list, tab_new, tab_activity, tab_chat = st.tabs(["My Tickets", "New Ticket", "Activity", "Help Chat"])

    with tab_list:
        my_tickets = my_tickets_all
        c1, c2 = st.columns(2)
        with c1:
            search = st.text_input("Search by title", "")
        with c2:
            loc_search = st.text_input("Search by location", "", placeholder="e.g. Building A, Room 204")
        if search.strip():
            my_tickets = [t for t in my_tickets if search.strip().lower() in t["title"].lower()]
        if loc_search.strip():
            my_tickets = [t for t in my_tickets if loc_search.strip().lower() in t["location"].lower()]

        if not my_tickets:
            st.info("You haven't raised any tickets yet.")
        else:
            st.caption(f"{len(my_tickets)} ticket(s)")
            for t in my_tickets:
                ui.render_ticket_card(t, user["id"], user["role"])

    with tab_new:
        st.subheader("Raise a new ticket")
        with st.form("new_ticket_form", clear_on_submit=True):
            title = st.text_input("Title", key="new_title")
            description = st.text_area("Description", key="new_desc")
            desc_len = len(description.strip())
            st.caption(f"{desc_len} / 20 characters minimum" + (" ✅" if desc_len >= 20 else ""))
            category = st.selectbox("Category", m.CATEGORIES, key="new_cat")
            location = st.text_input("Location", key="new_loc")
            priority = st.selectbox("Priority", m.PRIORITY_ORDER, key="new_pri")
            submitted_ticket = st.form_submit_button("Submit ticket", type="primary")

        if submitted_ticket:
            ok, errors, ticket = m.create_ticket(title, description, category, location, priority, user["id"])
            if ok:
                st.success(f"Ticket {ticket['id']} created with status Open. It now appears under My Tickets.")
                st.rerun()
            else:
                for e in errors:
                    st.error(e)

    with tab_activity:
        st.subheader("Your tickets' activity")
        ui.pdf_download_button(
            my_tickets_all, "⬇️ Download my task history (PDF)",
            f"servesmart_history_{user['id']}.pdf",
            report_title=f"ServeSmart — Task History for {user['name']}",
            key="pdf_student",
        )
        st.divider()
        events = []
        for t in my_tickets_all:
            for a in t["activity"]:
                events.append({"at": a["at"], "status": a["status"], "by": a["by"],
                                "ticket_id": t["id"], "title": t["title"]})
        events.sort(key=lambda e: e["at"], reverse=True)
        if not events:
            st.info("No activity yet.")
        else:
            for e in events:
                st.markdown(
                    f'<div class="feed-item"><span class="feed-time">{e["at"]}</span> — '
                    f'{ui.status_badge(e["status"])} <b>{e["ticket_id"]}</b> · {e["title"]} '
                    f'(by {m.name_for(e["by"])})</div>',
                    unsafe_allow_html=True,
                )


    with tab_chat:
        chatbot.render_chat(user)


def technician_view(user):
    st.title(f"🔧 Technician Dashboard — {user['name']}")

    assigned = [t for t in m.get_all_tickets() if t["technicianId"] == user["id"]]
    ui.metrics_row(assigned)
    st.divider()

    tab_tickets, tab_activity = st.tabs(["Assigned Tickets", "Activity"])

    with tab_tickets:
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.multiselect("Filter by status", m.STATUS_ORDER, default=[])
        with col2:
            priority_filter = st.multiselect("Filter by priority", m.PRIORITY_ORDER, default=[])
        with col3:
            loc_search = st.text_input("Search by location", "", placeholder="e.g. Dorm C")

        filtered = assigned
        if status_filter:
            filtered = [t for t in filtered if t["status"] in status_filter]
        if priority_filter:
            filtered = [t for t in filtered if t["priority"] in priority_filter]
        if loc_search.strip():
            filtered = [t for t in filtered if loc_search.strip().lower() in t["location"].lower()]
        filtered = sorted(filtered, key=m.priority_sort_key)

        st.caption(f"{len(filtered)} of {len(assigned)} assigned ticket(s) shown")

        if not filtered:
            st.info("No tickets match the current filters.")
        else:
            for t in filtered:
                ui.render_ticket_card(t, user["id"], user["role"], allow_advance=True)

    with tab_activity:
        st.subheader("Activity on your tickets")
        ui.pdf_download_button(
            assigned, "⬇️ Download my task history (PDF)",
            f"servesmart_history_{user['id']}.pdf",
            report_title=f"ServeSmart — Task History for {user['name']}",
            key="pdf_tech",
        )
        st.divider()
        events = []
        for t in assigned:
            for a in t["activity"]:
                events.append({"at": a["at"], "status": a["status"], "by": a["by"],
                                "ticket_id": t["id"], "title": t["title"]})
        events.sort(key=lambda e: e["at"], reverse=True)
        if not events:
            st.info("No activity yet.")
        else:
            for e in events:
                st.markdown(
                    f'<div class="feed-item"><span class="feed-time">{e["at"]}</span> — '
                    f'{ui.status_badge(e["status"])} <b>{e["ticket_id"]}</b> · {e["title"]} '
                    f'(by {m.name_for(e["by"])})</div>',
                    unsafe_allow_html=True,
                )


def admin_view(user):
    st.title(f"🗂️ Admin — {user['name']}")

    all_tickets = m.get_all_tickets()
    ui.metrics_row(all_tickets)
    st.divider()

    tab_unassigned, tab_all, tab_activity = st.tabs(
        ["Unassigned Tickets", "All Tickets (Reassign)", "Activity Log"]
    )

    with tab_unassigned:
        techs = m.get_users_by_role("Technician")
        unassigned = sorted([t for t in all_tickets if t["technicianId"] is None], key=m.priority_sort_key)
        loc_search_u = st.text_input("Search by location", "", placeholder="e.g. Library", key="loc_unassigned")
        if loc_search_u.strip():
            unassigned = [t for t in unassigned if loc_search_u.strip().lower() in t["location"].lower()]
        st.caption(f"{len(unassigned)} unassigned ticket(s)")
        for t in unassigned:
            with st.container(border=True):
                st.markdown(
                    f'{ui.priority_badge(t["priority"])}'
                    f'<span class="ticket-title">{t["title"]}</span><br>'
                    f'<span class="ticket-meta">{t["location"]}</span>',
                    unsafe_allow_html=True,
                )
                with st.expander("Details"):
                    st.write(t["description"])
                    if not techs:
                        st.warning("No technician accounts exist yet.")
                        continue
                    tech_pick = st.selectbox(
                        "Assign to technician", list(techs.keys()),
                        format_func=lambda k: techs[k], key=f"assign_{t['id']}"
                    )
                    if st.button("Assign", key=f"assign_btn_{t['id']}", type="primary"):
                        ok, msg = m.assign_ticket(t["id"], tech_pick, user["id"], user["role"])
                        (st.success if ok else st.error)(msg)
                        st.rerun()

    with tab_all:
        techs = m.get_users_by_role("Technician")
        loc_search_a = st.text_input("Search by location", "", placeholder="e.g. Building B", key="loc_all")
        visible_tickets = all_tickets
        if loc_search_a.strip():
            visible_tickets = [t for t in visible_tickets if loc_search_a.strip().lower() in t["location"].lower()]
        st.caption(f"{len(visible_tickets)} of {len(all_tickets)} ticket(s) shown")
        for t in sorted(visible_tickets, key=m.priority_sort_key):
            with st.container(border=True):
                st.markdown(ui.ticket_card_header_html(t), unsafe_allow_html=True)
                with st.expander("Details, reassign & history"):
                    st.write(t["description"])
                    if not techs:
                        st.warning("No technician accounts exist yet.")
                        continue
                    tech_ids = list(techs.keys())
                    default_idx = tech_ids.index(t["technicianId"]) if t["technicianId"] in tech_ids else 0
                    new_tech = st.selectbox(
                        "Reassign to", tech_ids, index=default_idx,
                        format_func=lambda k: techs[k], key=f"reassign_{t['id']}"
                    )
                    if st.button("Reassign", key=f"reassign_btn_{t['id']}", type="primary"):
                        ok, msg = m.assign_ticket(t["id"], new_tech, user["id"], user["role"])
                        (st.success if ok else st.error)(msg)
                        st.rerun()
                    st.write("**Status history:**")
                    for entry in t["activity"]:
                        st.markdown(
                            f'<div class="feed-item"><span class="feed-time">{entry["at"]}</span> — '
                            f'{ui.status_badge(entry["status"])} by {m.name_for(entry["by"])}</div>',
                            unsafe_allow_html=True,
                        )

    with tab_activity:
        st.subheader("All activity — every ticket, most recent first")
        ui.pdf_download_button(
            all_tickets, "⬇️ Download total task history (PDF)",
            "servesmart_total_history.pdf",
            report_title="ServeSmart — Total Task History (All Tickets)",
            key="pdf_admin",
        )
        st.divider()
        limit = st.slider("Events to show", 10, 200, 50, step=10)
        ui.global_activity_feed(limit=limit)