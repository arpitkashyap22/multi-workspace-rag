"""
Authentication view module.
Renders Neon Auth login and signup forms, handling session state initialization.
"""

import streamlit as st
from src.database import repository


def render_auth_gate() -> bool:
    """
    Renders the authentication form if no active user session exists.

    Returns:
        bool: True if user is authenticated, False otherwise.
    """
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user:
        return True

    col_left, col_center, col_right = st.columns([1, 1.8, 1])

    with col_center:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 2rem;'>
                <h1 style='font-size: 2.2rem; font-weight: 700; margin-bottom: 0.5rem;'>
                    🛡️ Multi-Workspace RAG
                </h1>
                <p style='color: #94a3b8; font-size: 1rem;'>
                    Tenant-isolated document intelligence with autonomous tool calling
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container():
            st.markdown('<div class="auth-container">', unsafe_allow_html=True)
            auth_mode = st.radio("Authentication Action", ["Sign In", "Create Account"], horizontal=True)

            with st.form("auth_form", clear_on_submit=False):
                email = st.text_input("Email Address", placeholder="name@example.com")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button(
                    "Sign In" if auth_mode == "Sign In" else "Create Account & Seed Workspace",
                    use_container_width=True,
                    type="primary",
                )

                if submitted:
                    if not email or not password:
                        st.error("Please provide both email and password.")
                    else:
                        with st.spinner("Authenticating with Neon Auth..."):
                            if auth_mode == "Sign In":
                                res = repository.login_user(email.strip(), password)
                            else:
                                res = repository.signup_user(email.strip(), password)

                        if res.get("success"):
                            st.session_state.user = {
                                "id": res["user_id"],
                                "email": res["email"],
                            }
                            # Fetch user workspaces
                            workspaces = repository.get_user_workspaces(res["user_id"])
                            if workspaces:
                                st.session_state.active_workspace_id = workspaces[0]["id"]
                            else:
                                ws = repository.create_workspace(res["user_id"], "General")
                                st.session_state.active_workspace_id = ws["id"]

                            st.success("Authenticated successfully!")
                            st.rerun()
                        else:
                            st.error(f"Error: {res.get('error', 'Authentication failed.')}")

            st.markdown("</div>", unsafe_allow_html=True)

    return False
