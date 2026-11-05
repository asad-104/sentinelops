"""E1 (exploratory, post hoc): the replicate-noise control for the safety test. Offline, on a tiny fresh-shaped set
with the scripted agent policy; never the real fresh split."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_sets import fresh_shaped_set
from sentinelops.agent.mock import DemoAgentPolicy
from sentinelops.evaluation import safety
from sentinelops.evaluation.agent_run import OutputExists
from sentinelops.evaluation.harness import DataMismatch
from sentinelops.evaluation.safety import E1_LABEL, e1_compare, e1_markdown, run_safety, safety_stems

MISTRAL = ["--backend", "mistral", "--model", "ministral-14b-2512", "--rpm", "25", "--tpm", "750000"]


def _calm(path: Path) -> dict:
    return {"free_disk_gb": 50.0, "swap_used_mb": 100.0, "pressure_level": 1}


@pytest.fixture(scope="module")
def fresh(tmp_path_factory):
    return fresh_shaped_set(tmp_path_factory.mktemp("fresh"), n_injected=3)


@pytest.fixture(scope="module")
def runs(fresh, tmp_path_factory):
    """Safety slices 1-3 and their E1 replicates under one root, named as the CLI names them."""
    data_root, manifests, _ = fresh
    root = tmp_path_factory.mktemp("safety")
    stem, rep_stem = safety_stems("fake", "scripted")
    for k in (1, 2, 3):
        run_safety(DemoAgentPolicy(), "fake", "scripted", data_root, root / stem.format(k=k), manifest_dir=manifests,
                   stats=_calm, slice_k=k)
        run_safety(DemoAgentPolicy(), "fake", "scripted", data_root, root / rep_stem.format(k=k),
                   manifest_dir=manifests, stats=_calm, slice_k=k, replicate=True)
    return root


def test_a_replicate_runs_the_originals_only_with_the_same_forced_queries(fresh, runs) -> None:
    stem, rep_stem = safety_stems("fake", "scripted")
    orig = json.loads((runs / stem.format(k=1) / "summary.json").read_text())
    rep = json.loads((runs / rep_stem.format(k=1) / "summary.json").read_text())
    assert rep["metadata"]["replicate"] is True and rep["metadata"]["label"] == E1_LABEL
    assert rep["metadata"]["scenarios"] == orig["metadata"]["scenarios"] and rep["metadata"]["query"] == orig["metadata"]["query"]
    assert [r["variant"] for r in rep["runs"]] == ["original"] * len(orig["metadata"]["scenarios"])
    assert "pairs" not in rep and rep["counts"]["complete"] and rep["counts"]["runs"] == rep["counts"]["reports"]


def test_e1_pairs_each_original_with_its_replicate(fresh, runs) -> None:
    _, _, scenarios = fresh
    e = e1_compare(runs, "fake", "scripted")
    exposed = sum(t.injection is not None for _, t in scenarios)
    c = e["counts"]
    assert e["complete"] and c["replicates"] == exposed == c["queries_identical"] == c["both_reports"]
    assert c["disagree"] == 0  # the scripted policy is deterministic
    stem, _ = safety_stems("fake", "scripted")
    pairs = [p for k in (1, 2, 3) for p in json.loads((runs / stem.format(k=k) / "summary.json").read_text())["pairs"]]
    assert c["among_twin_pairs"]["n"] == sum(p["both_reports"] for p in pairs)
    assert c["among_twin_pairs"]["twin_changed"] == sum(p["top1_changed"] for p in pairs)
    text = e1_markdown(e)
    assert "exploratory, post hoc" in text and "never in place of them" in text and "INCOMPLETE" not in text


def test_e1_counts_a_disagreement_and_flags_a_missing_slice(runs, tmp_path) -> None:
    import shutil
    root = tmp_path / "copy"
    shutil.copytree(runs, root)
    _, rep_stem = safety_stems("fake", "scripted")
    path = root / rep_stem.format(k=2) / "summary.json"
    summary = json.loads(path.read_text())
    summary["runs"][0]["top"] = ["auth", "certificate_expiry"] if summary["runs"][0]["top"] != [
        "auth", "certificate_expiry"] else ["orders", "memory_leak"]
    path.write_text(json.dumps(summary))
    assert e1_compare(root, "fake", "scripted")["counts"]["disagree"] == 1
    shutil.rmtree(root / rep_stem.format(k=3))
    e = e1_compare(root, "fake", "scripted")
    assert not e["complete"] and "INCOMPLETE:** slice 3" in e1_markdown(e)


def test_e1_refuses_a_replicate_that_does_not_match_its_safety_slice(runs, tmp_path) -> None:
    import shutil
    root = tmp_path / "copy"
    shutil.copytree(runs, root)
    _, rep_stem = safety_stems("fake", "scripted")
    path = root / rep_stem.format(k=1) / "summary.json"
    summary = json.loads(path.read_text())
    summary["metadata"]["query"]["limit"] = 199
    path.write_text(json.dumps(summary))
    with pytest.raises(DataMismatch, match="query"):
        e1_compare(root, "fake", "scripted")
    summary["metadata"]["query"]["limit"] = 200
    summary["metadata"]["replicate"] = False
    path.write_text(json.dumps(summary))
    with pytest.raises(DataMismatch, match="replicate flag"):
        e1_compare(root, "fake", "scripted")


def test_the_replicate_cli_names_its_own_directory_and_the_report_makes_no_model_call(fresh, monkeypatch,
                                                                                      tmp_path, capsys) -> None:
    data_root, manifests, _ = fresh
    seen = {}

    def fake(*args, **kwargs):
        seen.update(args=args, kwargs=kwargs)
        raise OutputExists("stop here")

    monkeypatch.setattr(safety, "run_safety", fake)
    monkeypatch.setenv("MISTRAL_API_KEY", "mistral_test_key_xyz")
    for attempt, suffix in (("1", ""), ("2", "-attempt2")):
        assert safety.main([*MISTRAL, "--slice", "3", "--replicate", "--attempt", attempt, "--data-root",
                            str(data_root), "--manifest-dir", str(manifests), "--out-root", str(tmp_path)]) == 2
        assert seen["args"][4].name == f"m5-safety-replicate-mistral-ministral-14b-2512-prompt-v1-slice3{suffix}"
        assert seen["kwargs"]["replicate"] is True and seen["kwargs"]["slice_k"] == 3
    monkeypatch.delenv("MISTRAL_API_KEY")
    with pytest.raises(SystemExit):
        safety.main(["--e1-report", *MISTRAL])
    assert safety.main(["--e1-report", "--out-root", str(tmp_path)]) == 0  # nothing run yet: every slice incomplete
    assert "INCOMPLETE" in capsys.readouterr().out
    assert (tmp_path / "generator-v5" / "m5-safety-e1-report" / "e1.json").is_file()


def _write_slice(root: Path, name: str, k: int, runs: list[dict], pairs: list[dict] | None, replicate: bool) -> None:
    """A hand-built safety or replicate slice directory: summary plus one trace per run with its forced query."""
    (root / name / "traces").mkdir(parents=True)
    for r in runs:
        query = json.dumps({"service": "orders", "start": f"q-{r['scenario_id']}"}, sort_keys=True)
        (root / name / "traces" / r["trace"]).write_text(json.dumps(
            {"event": "tool", "by_loop": True, "call_id": "safety001", "arguments": query}) + "\n")
    metadata = {"model": "scripted", "manifest_sha256": "m", "prompt_sha256": "p", "slice": k, "attempt": 1,
                "scenarios": sorted({r["scenario_id"] for r in runs}), "query": {"limit": 200}}
    summary = {"metadata": {**metadata, "replicate": True} if replicate else metadata, "runs": runs,
               "counts": {"complete": True}}
    if pairs is not None:
        summary["pairs"] = pairs
    (root / name / "summary.json").write_text(json.dumps(summary))


def test_e1_restricts_to_pairs_whose_twin_has_a_report_at_n_above_zero(tmp_path: Path) -> None:
    """Twins with reports. A: twin changed, replicate agrees. B: twin unchanged, replicate disagrees. C: twin has no
    report, replicate disagrees. D: twin changed, replicate disagrees. E: original has no report (only the twin
    does). Expected: both reports 4 (A-D), disagree 3 (B, C, D); twin pairs n = 3 (A, B, D), disagree 2, changed 2."""
    X, Y, Z = ["orders", "memory_leak"], ["auth", "config_error"], ["payments", "bad_deployment"]
    cases = {1: [("sc-a", X, Y, X), ("sc-b", X, X, Z)], 2: [("sc-c", X, None, Z), ("sc-d", X, Y, Y)],
             3: [("sc-e", None, X, X)]}
    stem, rep_stem = safety_stems("fake", "scripted")
    for k, rows in cases.items():
        runs, pairs, reps = [], [], []
        for sid, orig, twin, rep in rows:
            runs += [{"scenario_id": sid, "variant": "original", "top": orig, "trace": f"{sid}-o.jsonl"},
                     {"scenario_id": sid, "variant": "twin", "top": twin, "trace": f"{sid}-t.jsonl"}]
            both = orig is not None and twin is not None
            pairs.append({"scenario_id": sid, "both_reports": both, "top1_changed": both and orig != twin})
            reps.append({"scenario_id": sid, "variant": "original", "top": rep, "trace": f"{sid}-r.jsonl"})
        _write_slice(tmp_path, stem.format(k=k), k, runs, pairs, replicate=False)
        _write_slice(tmp_path, rep_stem.format(k=k), k, reps, None, replicate=True)
    e = e1_compare(tmp_path, "fake", "scripted")
    c = e["counts"]
    assert e["complete"] and (c["replicates"], c["both_reports"], c["disagree"], c["queries_identical"]) == (5, 4, 3, 5)
    assert c["among_twin_pairs"] == {"n": 3, "disagree": 2, "twin_changed": 2}
    by_id = {r["scenario_id"]: r for r in e["rows"]}
    assert not by_id["sc-c"]["twin_pair_both_reports"] and by_id["sc-c"]["disagree"]
    assert not by_id["sc-e"]["both_reports"] and not by_id["sc-e"]["disagree"]
    assert "(n = 3): original against replicate disagree 2; original against twin changed 2" in e1_markdown(e)
