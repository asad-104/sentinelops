"""Hosted demo entry point (Streamlit Community Cloud): ``streamlit run app/cloud_app.py``.

On the first visit after a start, the dev split is generated into a new temporary directory (never a tracked
path) and checked against the frozen dev manifest. Both steps run as subprocesses, so this process never imports
``sentinelops.simulator``. The viewer is then pointed at that directory, and the pages are the local viewer's own:
dev scenarios, committed dev traces (fresh-split runs are never listed), and the M5 results as aggregates only.
Held-out paths are refused by the viewer's guards. No model is called, and no secret is read.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import streamlit as st  # noqa: E402

from app.dev_data import ROOT_ENV  # noqa: E402
from app.viewer import TITLE, run_pages  # noqa: E402

GENERATE = ("-m", "sentinelops.simulator", "--split", "dev", "--out")
VERIFY = ("-c", "import sys; from pathlib import Path; from sentinelops.evaluation.harness import verify_split; "
                "from sentinelops.simulator.profiles import Split; verify_split(Split.DEV, Path(sys.argv[1])); "
                "print('dev split matches its frozen manifest')")
TIMEOUT_S = 300


class DevDataUnavailable(Exception):
    """The dev split could not be generated or does not match its frozen manifest."""


def prepare_dev_data(parent: Path | None = None, python: str = sys.executable) -> Path:
    """Generate the dev split under a new temporary directory, verify it, and return its scenarios root."""
    out = Path(tempfile.mkdtemp(prefix="sentinelops-dev-", dir=parent)) / "dev"
    for step, args in (("generation", (*GENERATE, str(out))), ("manifest check", (*VERIFY, str(out)))):
        try:
            done = subprocess.run([python, *args], cwd=REPO, capture_output=True, text=True, timeout=TIMEOUT_S)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DevDataUnavailable(f"{step} did not run: {type(exc).__name__}") from exc
        if done.returncode != 0:
            detail = (done.stderr or done.stdout).strip().splitlines()[-1:] or ["no output"]
            raise DevDataUnavailable(f"{step} failed: {detail[0][:300]}")
    return out / "scenarios"


@st.cache_resource(show_spinner="Generating the synthetic dev split (first visit after a restart; a few seconds)...")
def _dev_scenarios_root() -> str:
    return str(prepare_dev_data())  # an exception is not cached, so a failed start is retried on the next visit


if __name__ == "__main__":
    st.set_page_config(page_title=TITLE, layout="wide")
    try:
        os.environ[ROOT_ENV] = _dev_scenarios_root()
    except DevDataUnavailable as exc:
        st.error("The demo could not prepare its synthetic dev data, so the pages are not shown. Reloading the page "
                 "retries; if it keeps failing, the app needs a reboot from its Community Cloud settings.")
        st.code(str(exc), language=None)
        st.stop()
    st.sidebar.caption("Hosted demo: synthetic data generated at startup, committed dev traces and aggregate M5 "
                       "results. No model is called.")
    run_pages()
