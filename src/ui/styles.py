"""
UI styling module.
Encapsulates custom typography, modern glassmorphic design tokens, and CSS.
"""

import streamlit as st


def apply_custom_styles() -> None:
    """Injects modern dark theme styling tokens and typography into the Streamlit app."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif;
        }
        
        .stApp {
            background: radial-gradient(circle at 10% 20%, rgba(24, 30, 44, 0.4) 0%, rgba(13, 16, 23, 1) 90%);
        }

        /* Auth card */
        .auth-container {
            background: rgba(22, 27, 34, 0.85);
            border: 1px solid rgba(48, 54, 61, 0.8);
            border-radius: 16px;
            padding: 2.5rem;
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(12px);
        }
        
        /* Workspace Badge */
        .ws-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.15), rgba(59, 130, 246, 0.2));
            border: 1px solid rgba(56, 189, 248, 0.35);
            color: #38bdf8;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
        }

        /* Metric Cards */
        .metric-card {
            background: rgba(22, 27, 34, 0.6);
            border: 1px solid rgba(48, 54, 61, 0.6);
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
        }

        .citation-box {
            background: rgba(30, 41, 59, 0.5);
            border-left: 3px solid #38bdf8;
            padding: 8px 14px;
            border-radius: 0 8px 8px 0;
            margin-top: 8px;
            font-size: 0.85rem;
            color: #94a3b8;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
