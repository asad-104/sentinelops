"""Local viewer: dev-only guards, safe rendering of untrusted log text, no simulator imports."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from app.dev_data import (
    MANIFEST_ENV,
    ROOT_ENV,
    ViewerDataError,
    dev_ground_truth,
    dev_scenario_ids,
    dev_scenarios_root,
)
from sentinelops.models import LogRecord
from sentinelops.scenario_files import dump_json, write_observable
from sentinelops.simulator import FaultType, generate_scenario

from conftest import REPO_ROOT

PAGE = REPO_ROOT / "app" / "pages" / "m1_scenario_explorer.py"
HOSTILE = "**bold** <script>alert(1)</script> [click](http://evil.example)"


@pytest.fixture()
def dev_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, list]:
    """A two-scenario dev tree; the first scenario's first log carries hostile markup."""
    scenarios = [generate_scenario(11, 0, FaultType.MEMORY_LEAK), generate_scenario(11, 1, FaultType.CONFIG_ERROR)]
    obs, truth = scenarios[0]
    first = obs.logs[0]
    hostile_log = LogRecord(source_id=first.source_id, timestamp=first.timestamp, service=first.service,
                            level=first.level, message=HOSTILE)
    scenarios[0] = (obs.model_copy(update={"logs": (hostile_log, *obs.logs[1:])}), truth)

    root = tmp_path / "data" / "dev" / "scenarios"
    (tmp_path / "data" / "dev" / "ground_truth").mkdir(parents=True)
    for o, t in scenarios:
        write_observable(o, root / o.scenario_id)
        dump_json(tmp_path / "data" / "dev" / "ground_truth" / f"{o.scenario_id}.json", t.model_dump(mode="json"))
    manifest = tmp_path / "dev.json"
    manifest.write_text(json.dumps({"split": "dev", "scenario_ids": [o.scenario_id for o, _ in scenarios]}))
    monkeypatch.setenv(ROOT_ENV, str(root))
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    return root, scenarios


# Guards (no Streamlit needed)

@pytest.mark.parametrize("bad", ["data/heldout/scenarios", "data/HeldOut-v2/scenarios", "data/dev", "data/dev/ground_truth"])
def test_root_guard_rejects_heldout_and_non_scenario_dirs(tmp_path: Path, bad: str) -> None:
    with pytest.raises(ViewerDataError):
        dev_scenarios_root(str(tmp_path / bad))


def test_manifest_ids_without_a_directory_are_not_listed(dev_root: tuple[Path, list], tmp_path: Path) -> None:
    root, scenarios = dev_root
    manifest = tmp_path / "with_ghost.json"
    ids = [o.scenario_id for o, _ in scenarios]
    manifest.write_text(json.dumps({"split": "dev", "scenario_ids": [*ids, "sc-0000000000"]}))
    assert dev_scenario_ids(root, manifest) == ids


def test_non_dev_manifest_is_refused(dev_root: tuple[Path, list], tmp_path: Path) -> None:
    root, _ = dev_root
    manifest = tmp_path / "other.json"
    manifest.write_text(json.dumps({"split": "heldout_like", "scenario_ids": []}))
    with pytest.raises(ViewerDataError):
        dev_scenario_ids(root, manifest)


def test_ground_truth_reader(dev_root: tuple[Path, list]) -> None:
    root, scenarios = dev_root
    obs, truth = scenarios[1]
    assert dev_ground_truth(root, obs.scenario_id) == {
        "fault_type": truth.diagnosis.fault_type.value,
        "root_service": truth.diagnosis.service.value,
        "tier": truth.tier.value,
        "onset": truth.model_dump(mode="json")["onset"],
    }
    for bad_id in ("../../heldout/x", "sc-../../etc", "SC-0123456789"):
        with pytest.raises(ViewerDataError):
            dev_ground_truth(root, bad_id)


def test_ground_truth_reader_refuses_heldout_tree(tmp_path: Path) -> None:
    with pytest.raises(ViewerDataError):
        dev_ground_truth(tmp_path / "data" / "heldout" / "scenarios", "sc-0123456789")


# Import boundaries

def _imports(path: Path) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


@pytest.mark.parametrize("path", sorted((REPO_ROOT / "app").rglob("*.py")), ids=lambda p: p.name)
def test_viewer_never_imports_the_simulator(path: Path) -> None:
    assert not [m for m in _imports(path) if m.startswith("sentinelops.simulator")]


def test_core_package_never_imports_streamlit_or_pandas() -> None:
    offenders = [
        str(p.relative_to(REPO_ROOT)) for p in (REPO_ROOT / "sentinelops").rglob("*.py")
        if any(m.split(".")[0] in ("streamlit", "pandas") for m in _imports(p))
    ]
    assert not offenders


# Rendering (needs Streamlit)

@pytest.fixture()
def app_test(dev_root: tuple[Path, list]):
    testing = pytest.importorskip("streamlit.testing.v1")
    at = testing.AppTest.from_file(str(PAGE), default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_page_renders_core_sections(app_test) -> None:
    headers = [h.value for h in app_test.subheader]
    assert headers == ["Alert", "Timeline", "Dependencies", "Metrics", "Log search", "Record lookup"]
    assert app_test.dataframe, "timeline and log tables should render"


def test_reveal_answer_is_collapsed_and_reads_dev_ground_truth(app_test, dev_root: tuple[Path, list]) -> None:
    _, scenarios = dev_root
    expander = app_test.expander[0]
    assert expander.label == "Reveal answer (dev only)"
    assert expander.proto.expanded is False
    shown = json.loads(expander.json[0].proto.body)
    assert shown["fault_type"] == scenarios[0][1].diagnosis.fault_type.value


def test_truncation_warning_appears_above_chart(app_test) -> None:
    assert not [w for w in app_test.warning if "points per service" in w.value]
    app_test.number_input(key="metric_limit").set_value(10).run()
    assert [w for w in app_test.warning if "points per service" in w.value]


def test_compare_all_services_draws_one_chart(app_test) -> None:
    app_test.selectbox(key="metric_name").set_value("db_pool_utilization_pct")
    app_test.toggle(key="metric_compare").set_value(True).run()
    assert not app_test.exception
    assert any("api-gateway (unsupported_metric)" in c.value for c in app_test.caption)


def test_unsupported_metric_shows_structured_error(app_test) -> None:
    app_test.selectbox(key="metric_service").set_value("api-gateway")
    app_test.selectbox(key="metric_name").set_value("db_pool_utilization_pct").run()
    assert any("unsupported_metric" in c.value for c in app_test.code)


def test_log_search_form_applies_filters_on_submit(app_test) -> None:
    app_test.text_input(key="log_contains").set_value("evil.example")  # only the hostile line has this
    app_test.number_input(key="log_limit").set_value(5)
    app_test.button[0].click().run()  # form values only apply on submit
    tables = [df.value for df in app_test.dataframe if "message" in df.value.columns]
    assert len(tables) == 1 and list(tables[0]["message"]) == [HOSTILE]
    app_test.text_input(key="log_contains").set_value("<script>")
    app_test.button[0].click().run()
    assert [m.value for m in app_test.metric if m.label == "Returned"] == ["5"], "limit applies"


def test_hostile_log_text_is_shown_literally_never_as_markdown(app_test) -> None:
    messages = [m for df in app_test.dataframe if "message" in df.value.columns for m in df.value["message"]]
    assert HOSTILE in messages
    rendered_markup = [md.value for md in app_test.markdown if "<script>" in md.value or "**bold**" in md.value]
    assert not rendered_markup


# M2 page: tier counts and dev results

M2_PAGE = REPO_ROOT / "app" / "pages" / "m2_tiers_and_results.py"


def _write_results(results_dir: Path, scenarios: list, split: str = "dev") -> None:
    from sentinelops.evaluation.metrics import ScenarioScore, summarize

    results_dir.mkdir(parents=True)
    for i, name in enumerate(("rule_based", "keyword_only", "latest_change", "alert_service")):
        scores = [ScenarioScore(scenario_id=o.scenario_id, tier=t.tier.value, fault_type=t.diagnosis.fault_type.value,
                                top1=i == 0, top3=True, service_top1=True, cited=1, headline_valid=1, lenient_valid=1,
                                strict_valid=1, fabricated=0, hypotheses=1, unsupported=0, missing_named=None,
                                injection_present=False, injection_cited=False, injection_changed=None,
                                injection_changed_to_claim=None,
                                tool_calls=1, duration_s=0.0, cost_usd=0.0) for o, t in scenarios]
        (results_dir / f"dev-{name}.json").write_text(json.dumps(
            {"investigator": name, "split": split, "metadata": {}, "summary": summarize(scores), "scenarios": []}))


@pytest.fixture()
def results_dir(dev_root: tuple[Path, list], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from app.dev_data import RESULTS_ENV

    root = tmp_path / "results"
    _write_results(root / "generator-v4", dev_root[1])
    _write_results(root / "generator-v3", dev_root[1])
    monkeypatch.setenv(RESULTS_ENV, str(root))
    return root


def test_result_versions_newest_first_and_dev_only(results_dir: Path) -> None:
    from app.dev_data import dev_result_versions, dev_results

    assert dev_result_versions(results_dir) == ["generator-v4", "generator-v3"]
    loaded = dev_results(results_dir, "generator-v4")
    assert set(loaded.investigators) == {"rule_based", "keyword_only", "latest_change", "alert_service"}
    assert loaded.skipped == []
    with pytest.raises(ViewerDataError):
        dev_results(results_dir, "../heldout")


def test_non_dev_result_files_are_refused(tmp_path: Path, dev_root: tuple[Path, list]) -> None:
    from app.dev_data import dev_results

    _write_results(tmp_path / "generator-v9", dev_root[1], split="heldout")
    with pytest.raises(ViewerDataError):
        dev_results(tmp_path, "generator-v9")


def test_tier_counts_match_ground_truth(dev_root: tuple[Path, list]) -> None:
    from app.dev_data import dev_tier_counts

    root, scenarios = dev_root
    rows = dev_tier_counts(root, [o.scenario_id for o, _ in scenarios])
    assert sum(r["scenarios"] for r in rows) == len(scenarios)
    assert {(r["tier"], r["fault_type"]) for r in rows} == {(t.tier.value, t.diagnosis.fault_type.value) for _, t in scenarios}


def test_m2_page_draws_floors_as_reference_lines(dev_root: tuple[Path, list], results_dir: Path) -> None:
    testing = pytest.importorskip("streamlit.testing.v1")
    at = testing.AppTest.from_file(str(M2_PAGE), default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert [h.value for h in at.subheader] == ["Dev tier counts", "Dev results"]
    charts = at.get("vega_lite_chart")
    assert len(charts) == 1
    spec = charts[0].proto.spec
    assert '"tick"' in spec and '"bar"' in spec and "strokeDash" in spec
    at.radio(key="results_metric").set_value("Top-3").run()
    at.selectbox(key="results_version").set_value("generator-v3").run()
    assert not at.exception


INVESTIGATORS = ("rule_based", "keyword_only", "latest_change", "alert_service")
SLICES = ("overall", "standard", "ambiguous", "missing_evidence")


def _write_ablation(results_dir: Path) -> dict:
    """An ablation file in the shape ``sentinelops.evaluation.ablation`` writes, built with its own counter."""
    from sentinelops.evaluation.ablation import paired_counts

    t, w = ("orders", "bad_deployment"), ("auth", "memory_leak")
    triples = {"injection": [(t, t, t)] * 12, "overlap": [(t, w, t)] * 3 + [(t, t, t)] * 7,
               "decoy": [(t, w, w)] * 10, "gap": [(t, w, t)] * 2 + [(t, t, w)] * 8}
    data = {"split": "dev", "metadata": {"generator_version": "5", "manifest_sha256": "0" * 64,
                                         "git_commit": "test", "call_budget": 200},
            "ablation": {m: {name: paired_counts(tr) for name in INVESTIGATORS} for m, tr in triples.items()}}
    dump_json(results_dir / "dev-ablation.json", data)
    (results_dir / "dev-ablation.md").write_text("# dev paired ablation\n")
    (results_dir / "dev-summary.md").write_text("# dev results\n")
    return data


def _assert_m2_page_matches(at, version_dir: Path) -> None:
    """The results table shows each investigator's k/n exactly as its file states, for every slice."""
    files = {json.loads(p.read_text())["investigator"]: json.loads(p.read_text())["summary"]
             for p in version_dir.glob("dev-*.json") if "investigator" in json.loads(p.read_text())}
    table = next(df.value for df in at.dataframe if "overall" in df.value.columns)
    assert set(table.index) == set(files)
    for name, summary in files.items():
        for slice_ in SLICES:
            rate = summary["overall" if slice_ == "overall" else "per_tier"]
            rate = rate["top1"] if slice_ == "overall" else rate[slice_]["top1"]
            cell = table.loc[name, slice_]
            assert cell == "n/a" if not rate["n"] else cell.startswith(f"{rate['k']}/{rate['n']} "), (name, slice_)


def test_dev_results_skips_non_investigator_files(tmp_path: Path, dev_root: tuple[Path, list]) -> None:
    from app.dev_data import dev_ablation, dev_results

    version = tmp_path / "generator-v5"
    _write_results(version, dev_root[1])
    data = _write_ablation(version)
    (version / "dev-broken.json").write_text("{not json")
    loaded = dev_results(tmp_path, "generator-v5")
    assert set(loaded.investigators) == set(INVESTIGATORS)
    assert loaded.skipped == ["dev-ablation.json", "dev-broken.json"]
    assert dev_ablation(tmp_path, "generator-v5") == data
    assert dev_ablation(tmp_path, "generator-v4") is None


def test_m2_page_renders_v5_layout_with_ablation(dev_root: tuple[Path, list], tmp_path: Path,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    testing = pytest.importorskip("streamlit.testing.v1")
    from app.dev_data import RESULTS_ENV

    root = tmp_path / "results"
    _write_results(root / "generator-v5", dev_root[1])
    ablation = _write_ablation(root / "generator-v5")
    _write_results(root / "generator-v4", dev_root[1])
    monkeypatch.setenv(RESULTS_ENV, str(root))
    at = testing.AppTest.from_file(str(M2_PAGE), default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert [h.value for h in at.subheader] == ["Dev tier counts", "Dev results", "Paired ablation"]
    assert any("dev-ablation.json" in i.value for i in at.info)
    _assert_m2_page_matches(at, root / "generator-v5")
    flips = next(df.value for df in at.dataframe if "mechanism" in df.value.columns)
    for _, row in flips.iterrows():
        per = ablation["ablation"][row["mechanism"]]
        assert row["n"] == per["rule_based"]["n"]
        assert all(row[name] == per[name]["correct_only_without"] for name in INVESTIGATORS)
    assert "not effect size" in " ".join(c.value for c in at.caption)
    # Versions without an ablation file show no ablation panel and no skipped-file note.
    at.selectbox(key="results_version").set_value("generator-v4").run()
    assert not at.exception and "Paired ablation" not in [h.value for h in at.subheader] and not at.info


@pytest.mark.parametrize("version", sorted(p.name for p in (REPO_ROOT / "eval" / "results").glob("generator-v*")))
def test_m2_page_renders_committed_results(version: str, dev_root: tuple[Path, list],
                                           monkeypatch: pytest.MonkeyPatch) -> None:
    """Render against the real eval/results (dev results are committed); numbers must match the files."""
    testing = pytest.importorskip("streamlit.testing.v1")
    from app.dev_data import RESULTS_ENV, dev_ablation

    results = REPO_ROOT / "eval" / "results"
    monkeypatch.setenv(RESULTS_ENV, str(results))
    at = testing.AppTest.from_file(str(M2_PAGE), default_timeout=60)
    at.run()
    at.selectbox(key="results_version").set_value(version).run()
    assert not at.exception, [e.value for e in at.exception]
    _assert_m2_page_matches(at, results / version)
    ablation = dev_ablation(results, version)
    assert ("Paired ablation" in [h.value for h in at.subheader]) is (ablation is not None)


def test_malformed_files_raise_viewer_errors_not_crashes(tmp_path: Path, dev_root: tuple[Path, list]) -> None:
    from app.dev_data import dev_results

    root, scenarios = dev_root
    sid = scenarios[0][0].scenario_id
    (root.parent / "ground_truth" / f"{sid}.json").write_text(json.dumps({"tier": "standard"}))
    with pytest.raises(ViewerDataError):
        dev_ground_truth(root, sid)
    version = tmp_path / "generator-v5"
    version.mkdir()
    (version / "dev-old.json").write_text(json.dumps({"split": "dev", "investigator": "x", "summary": {"n": 1}}))
    assert dev_results(tmp_path, "generator-v5") == ({}, ["dev-old.json"])
