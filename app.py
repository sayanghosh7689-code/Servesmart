"""
app.py — entry point / routing for ServeSmart.

Run:
    pip install -r requirements.txt
    streamlit run app.py
"""

import streamlit as st
import models as m
import views as v
import ui


def main():
    st.set_page_config(page_title="ServeSmart", page_icon="🛠️", layout="wide")
    ui.inject_css()
    m.init_db()

    if "user" not in st.session_state:
        st.session_state.user = None
    user = st.session_state.user

    if user:
        with st.sidebar:
            st.markdown(
                f"""
                <div class="user-card">
                    <div class="name">{user['name']}</div>
                    <div class="role">{user['role']}</div>
                    <div class="id">ID: {user['id']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Log out", use_container_width=True):
                st.session_state.user = None
                st.rerun()

    if not user:
        v.login_view()
        return

    if user["role"] == "Student":
        v.student_view(user)
    elif user["role"] == "Technician":
        v.technician_view(user)
    elif user["role"] == "Admin":
        v.admin_view(user)


if __name__ == "__main__":
    main()
