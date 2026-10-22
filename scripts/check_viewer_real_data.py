"""Standing check: render every viewer page headlessly against the real data (no env overrides).

Run before calling any milestone done:  .venv/bin/python scripts/check_viewer_real_data.py
M1: every dev scenario in the manifest renders without exceptions. M2: every results version
renders without exceptions, and every table cell matches the result files exactly. Dev data only;
the viewer's own guards refuse held-out paths.
"""
import json
import sys
from collections import Counter
from pathlib import Path
from streamlit.testing.v1 import AppTest

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo))
results = repo / "eval" / "results"
# M1: every dev scenario.
m1 = AppTest.from_file(str(repo / "app/pages/m1_scenario_explorer.py"), default_timeout=60)
m1.run()
assert not m1.exception, [e.value for e in m1.exception]
ids = json.loads((repo / "eval/manifests/dev.json").read_text())["scenario_ids"]
assert list(m1.sidebar.selectbox(key="scenario").options) == ids, "M1 does not list exactly the dev manifest"
for sid in ids:
    m1.sidebar.selectbox(key="scenario").set_value(sid).run()
    assert not m1.exception, (sid, [e.value for e in m1.exception])
print(f"M1: {len(ids)} dev scenarios render without exceptions")

# M2: every results version.
at = AppTest.from_file(str(repo / "app/pages/m2_tiers_and_results.py"), default_timeout=60)
at.run()
assert not at.exception, [e.value for e in at.exception]

# Tier counts vs dev ground truth on disk.
gt = [json.loads(p.read_text()) for p in (repo / "data/dev/ground_truth").glob("*.json")]
tiers = at.dataframe[0].value
expected = Counter((t["diagnosis"]["fault_type"], t["tier"]) for t in gt)
assert all(tiers.loc[f, t] == n for (f, t), n in expected.items()) and tiers.loc["total"].sum() == len(gt)
print(f"M2 tier counts: {len(gt)} scenarios match ground truth")

versions = at.selectbox(key="results_version").options
for version in versions:
    for metric_label, key in (("Top-1", "top1"), ("Top-3", "top3"), ("Service top-1", "service_top1")):
        at.selectbox(key="results_version").set_value(version)
        at.radio(key="results_metric").set_value(metric_label).run()
        assert not at.exception, (version, [e.value for e in at.exception])
        table = next(df.value for df in at.dataframe if "overall" in df.value.columns)
        checked = 0
        for p in sorted((results / version).glob("dev-*.json")):
            data = json.loads(p.read_text())
            if "investigator" not in data:
                continue
            for slice_ in ("overall", "standard", "ambiguous", "missing_evidence"):
                block = data["summary"]["overall"] if slice_ == "overall" else data["summary"]["per_tier"][slice_]
                r = block[key]
                cell = table.loc[data["investigator"], slice_]
                want = f"{r['k']}/{r['n']} ({r['pct']:.0f}%, {r['ci95'][0]:.0f}–{r['ci95'][1]:.0f})"
                assert cell == want, (version, data["investigator"], slice_, cell, want)
                checked += 1
    subheaders = [h.value for h in at.subheader]
    line = f"{version}: no exceptions; {checked} cells x 3 metrics match files; subheaders={subheaders}"
    abl = results / version / "dev-ablation.json"
    if abl.exists():
        flips = next(df.value for df in at.dataframe if "mechanism" in df.value.columns)
        data = json.loads(abl.read_text())["ablation"]
        for _, row in flips.iterrows():
            for name, c in data[row["mechanism"]].items():
                assert row[name] == c["correct_only_without"] and row["n"] == c["n"]
        line += f"; ablation table {len(flips)} rows match file; note: {[i.value for i in at.info]}"
    print(line)
print("OK: viewer renders against real data")
