"""Entry point: ``.venv/bin/streamlit run app/viewer.py`` (binds to 127.0.0.1, dev data only).

The page list is shared with the hosted demo's entry point (``app/cloud_app.py``).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

TITLE = "SentinelOps viewer (dev only)"
PAGES = (
    ("pages/m1_scenario_explorer.py", "M1 · Scenario explorer"),
    ("pages/m2_tiers_and_results.py", "M2 · Tiers and dev results"),
    ("pages/m3_pilot_traces.py", "M3 · Pilot traces"),
    ("pages/m4_agent_runs.py", "M4 · Agent runs"),
    ("pages/m5_comparison.py", "M5 · Headline comparison"),
)


def run_pages() -> None:
    st.navigation([st.Page(path, title=title) for path, title in PAGES]).run()


if __name__ == "__main__":
    st.set_page_config(page_title=TITLE, layout="wide")
    run_pages()
