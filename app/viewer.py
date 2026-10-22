"""Entry point: ``.venv/bin/streamlit run app/viewer.py`` (binds to 127.0.0.1, dev data only)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="SentinelOps viewer (dev only)", layout="wide")
st.navigation([
    st.Page("pages/m1_scenario_explorer.py", title="M1 · Scenario explorer"),
]).run()
