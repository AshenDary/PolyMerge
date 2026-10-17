"""Host the complete PolyMerge frontend in Streamlit."""

import os
from urllib.parse import urlsplit

import streamlit as st


FRONTEND_URL = os.environ.get(
    "POLYMERGE_FRONTEND_URL",
    os.environ.get("POLYMERGE_API_URL", "http://127.0.0.1:3000"),
).rstrip("/") + "/"

st.set_page_config(page_title="PolyMerge Research Dashboard", page_icon="🧪", layout="wide", initial_sidebar_state="collapsed")
parsed_url = urlsplit(FRONTEND_URL)
local = parsed_url.hostname in {"localhost", "127.0.0.1"}
if (parsed_url.scheme != "https" and not (local and parsed_url.scheme == "http")) or parsed_url.username or parsed_url.password or parsed_url.query or parsed_url.fragment:
    st.error("The research application URL is not configured securely.")
    st.stop()
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

st.iframe(FRONTEND_URL, height=800, tab_index=0, alt="PolyMerge research interface")
