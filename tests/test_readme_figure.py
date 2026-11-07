"""The README figure is generated from the committed M5 analysis and must not go stale."""

from __future__ import annotations

import importlib.util
import json
import re

from conftest import REPO_ROOT

spec = importlib.util.spec_from_file_location("make_readme_figure", REPO_ROOT / "scripts" / "make_readme_figure.py")
fig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fig)


def test_committed_figures_match_the_analysis_file() -> None:
    for name, svg in fig.render().items():
        assert (REPO_ROOT / "docs" / "figures" / name).read_text(encoding="utf-8") == svg, (
            f"{name} is stale: run .venv/bin/python scripts/make_readme_figure.py")


def test_the_figure_shows_the_d1_counts_and_every_arm() -> None:
    a = json.loads(fig.ANALYSIS.read_text())
    svg = fig.render()["m5-at-a-glance-light.svg"]
    p = a["primary"]
    assert f'{p["a_right_b_wrong"]} against {p["b_right_a_wrong"]}' in svg and f'p = {p["p_two_sided"]:.3f}' in svg
    for key, label in fig.ARMS:
        r = a["arms"][key]["top1"]
        assert f'>{r["k"]}/{r["n"]}<' in svg and f">{label}<" in svg
    assert not re.search(r"sc-[0-9a-f]{10}", svg)
