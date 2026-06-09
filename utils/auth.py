"""
auth.py
───────
Simple password gate for the terminal.
Reads TERMINAL_PASSWORD from environment / Streamlit secrets.
If unset, the gate is bypassed (useful for localhost).
"""

import os
import streamlit as st


def require_password() -> None:
    """
    Call at the top of app.py (and any page you want gated)
    after st.set_page_config(). Blocks the page until the
    correct password is entered.
    """
    # Try Streamlit secrets first (works on Streamlit Cloud),
    # fall back to env var (works on Render, Railway, local .env).
    expected = ""
    try:
        expected = st.secrets.get("TERMINAL_PASSWORD", "")  # type: ignore[attr-defined]
    except Exception:
        pass
    if not expected:
        expected = os.environ.get("TERMINAL_PASSWORD", "")

    # No password configured → no gate (localhost convenience)
    if not expected:
        return

    if st.session_state.get("_auth_ok"):
        return

    st.markdown(
        """<div style="
            max-width: 380px; margin: 6rem auto 0;
            padding: 2rem; border: 1px solid #1e2d45;
            border-radius: 8px; background: #0f1929;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        ">
          <div style="font-size:0.62rem;font-weight:700;letter-spacing:0.11em;
                      color:#3b82f6;text-transform:uppercase;margin-bottom:0.6rem;">
            Access Required
          </div>
          <div style="font-size:1rem;font-weight:600;color:#e2e8f0;margin-bottom:0.3rem;">
            India Markets Terminal
          </div>
          <div style="font-size:0.78rem;color:#64748b;margin-bottom:1.5rem;">
            Enter your access password to continue.
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

    with st.container():
        cols = st.columns([1, 2, 1])
        with cols[1]:
            pw = st.text_input(
                "Password", type="password",
                key="_pw_input", label_visibility="collapsed",
                placeholder="Enter password…",
            )
            if pw:
                if pw == expected:
                    st.session_state["_auth_ok"] = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")

    st.stop()
