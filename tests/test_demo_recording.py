"""The README's demo recording: dev runs only, small, and within 20-40 s. The script itself needs Playwright and runs
outside the project's requirements, so it is checked as text here, not imported."""

from __future__ import annotations

import json
import re

import pytest

from conftest import REPO_ROOT

SCRIPT = (REPO_ROOT / "scripts" / "record_demo.py").read_text()
FIGURES = REPO_ROOT / "docs" / "figures"


def test_the_recording_names_only_dev_runs_and_dev_scenarios() -> None:
    dev = set(json.loads((REPO_ROOT / "eval" / "manifests" / "dev.json").read_text())["scenario_ids"])
    named = set(re.findall(r"sc-[0-9a-f]{10}", SCRIPT))
    assert named and named <= dev
    assert 'RUN = "generator-v5/mistral-ministral-14b-2512"' in SCRIPT
    shots = SCRIPT[SCRIPT.index("SHOTS = ["):SCRIPT.index("CSS = ")]  # the shot list and the end caption
    assert "Agent runs" in shots and not re.search(r"m5|fresh|held", shots, re.I)


def test_the_gif_is_small_and_20_to_40_seconds_with_a_still_fallback() -> None:
    image = pytest.importorskip("PIL.Image")
    gif = FIGURES / "demo.gif"
    assert gif.stat().st_size < 2_000_000
    with image.open(gif) as im:
        durations = []
        for i in range(im.n_frames):
            im.seek(i)
            durations.append(im.info["duration"])
        assert im.size[0] <= 1000 and 20_000 <= sum(durations) <= 40_000
    assert (FIGURES / "demo-still.png").stat().st_size < 500_000
    readme = (REPO_ROOT / "README.md").read_text()
    assert 'srcset="docs/figures/demo-still.png"' in readme and 'src="docs/figures/demo.gif"' in readme
