"""Host the complete PolyMerge frontend in Streamlit."""

import os

import streamlit as st
import streamlit.components.v1 as components


FRONTEND_URL = os.environ.get(
    "POLYMERGE_FRONTEND_URL",
    os.environ.get("POLYMERGE_API_URL", "http://127.0.0.1:3000"),
).rstrip("/") + "/"

st.set_page_config(page_title="PolyMerge Research Dashboard", page_icon="🧪", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
.stApp { background: #eef3ef; }
[data-testid="stMain"] { padding-top: 0 !important; }
[data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"], .block-container { max-width: none !important; padding: 0 !important; margin: 0 !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stHeader"] { display: none; }
[data-testid="stIFrame"] { height: 100vh !important; margin: 0 !important; padding: 0 !important; }
iframe { display: block; width: 100%; height: 100vh !important; min-height: 100vh; border: 0; margin: 0; padding: 0; }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { scroll-behavior: auto !important; animation-duration: .01ms !important; transition-duration: .01ms !important; } }
</style>
""", unsafe_allow_html=True)

components.iframe(FRONTEND_URL, height=800, scrolling=True)
