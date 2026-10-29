"""M5 stage C: the single-pass baseline and its no-timeline arm. Bundle purity (tool data only, no ground truth),
the frozen rule, reductions, validation and repair, provider stops, frozen hashes, and the runner. Offline."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from agent_sets import generated_set
from sentinelops.agent import single_pass as sp
from sentinelops.agent.single_pass import RULE, SinglePassInvestigator, collect, render, single_pass_sha256
from sentinelops.agent.states import AgentBounds
from sentinelops.evaluation.agent_run import M5_DEV_SCENARIOS
from sentinelops.llm.client import LLMError
from sentinelops.llm.mock import ScriptedClient, call, text
from sentinelops.report import InvestigationFailed
from sentinelops.tools import ToolSet

FROZEN = {"full": "2bf74a3f683b05653353f3018fe583dd886495f8a3a28b4a7df5885c4a9495da",
          "no-timeline": "e4acb736ce5be6d76a4c4161c83cae2a6a32ad2d511da0d4fcc335a044d352a4"}
GROUND_TRUTH_KEYS = ("template_id", "variant_id", "tier", "diagnosis", "trigger_source_id", "red_herring", "decoy",
                     "fault_log_source_ids", "overlap_log_source_ids", "injection", "mechanisms_off", "missing_evidence",
                     "metric_blip", "log_provenance", "origin")


@pytest.fixture(scope="module")
def gen(tmp_path_factory):
    return generated_set(tmp_path_factory.mktemp("sp"))


def _tools(gen, i=0, twin=False):
    data_root, _, scenarios = gen
    root = data_root / "twins" if twin else data_root
    return ToolSet.from_directory(root / "scenarios", scenarios[i][0].scenario_id), scenarios[i]


def test_hashes_are_frozen_and_differ_by_arm() -> None:
    assert {v: single_pass_sha256(v) for v in sp.VARIANTS} == FROZEN
    with pytest.raises(ValueError):
        single_pass_sha256("other")


def test_frozen_rule_values_are_the_preregistered_ones() -> None:
    assert (RULE.slices, RULE.error_per_slice, RULE.warn_per_slice, RULE.message_cap) == (6, 1, 1, 160)
    assert RULE.reductions == ("message_cap_100", "slices_4", "drop_warn", "drop_flat_metrics")
    assert sp.METRICS == ("latency_p95_ms", "error_rate", "cpu_pct", "memory_pct", "request_rate",
                          "db_pool_utilization_pct")


def test_the_bundle_holds_only_tool_data_and_no_ground_truth(gen) -> None:
    for i in range(len(gen[2])):
        tools, (observable, truth) = _tools(gen, i)
        blocks = collect(tools, "full")
        assert blocks["changes"] == tools.call("get_timeline", {"start": blocks["window"][0]["window_start"],
                                                                "end": blocks["window"][0]["window_end"],
                                                                "limit": 200}).model_dump(mode="json")["items"]
        assert blocks["alert"] == tools.call("get_alert", {}).model_dump(mode="json")["items"]
        for log in blocks["logs"]:
            returned = tools.call("get_record", {"source_id": log["source_id"]}).model_dump(mode="json")["items"][0]
            assert log == returned  # an unmodified tool record before rendering
        text_ = "\n".join(m.content for m in render(blocks, RULE.message_cap, False)[1:])
        assert not [k for k in GROUND_TRUTH_KEYS if f'"{k}"' in text_]
        assert truth.diagnosis.fault_type.value not in text_ or truth.diagnosis.fault_type.value in json.dumps(
            [*blocks["logs"], *blocks["alert"]])  # a fault name may appear only inside tool-returned text
        ids = sp._ids(text_)
        existing = {observable.alert.source_id, *(r.source_id for rs in (observable.logs, observable.metrics,
                    observable.deployments, observable.config_changes, observable.dependencies) for r in rs)}
        assert ids <= existing


def test_log_caps_levels_and_message_prefix(gen) -> None:
    tools, _ = _tools(gen, 1)
    blocks = collect(tools, "full")
    per = {}
    for log in blocks["logs"]:
        per.setdefault((log["service"], log["level"]), 0)
        per[(log["service"], log["level"])] += 1
    assert all(n <= RULE.slices for n in per.values()) and {lvl for _, lvl in per} <= {"ERROR", "WARN"}
    rendered = render(blocks, RULE.message_cap, False)
    log_block = next(m.content for m in rendered if m.content.startswith("DATA logs"))
    for line in log_block.splitlines()[1:]:
        item = json.loads(line)
        assert len(item["message"]) <= 160
        original = next(log for log in blocks["logs"] if log["source_id"] == item["source_id"])
        assert original["message"].startswith(item["message"])  # a prefix of what the tool returned


def test_the_no_timeline_arm_omits_only_the_changes_block(gen) -> None:
    tools, _ = _tools(gen, 2)
    full, bare = collect(tools, "full"), collect(tools, "no-timeline")
    assert "changes" in full and "changes" not in bare
    assert {k: v for k, v in full.items() if k != "changes"} == bare
    names = [m.content.split(" ", 2)[1] for m in render(bare, 160, False)[1:]]
    assert names == ["alert", "window", "dependencies", "logs", "metrics"]


def _valid_report(ids: list[str]) -> dict:
    return {"summary": "s", "hypotheses": [{"rank": 1, "service": "orders", "fault_type": "memory_leak",
                                            "confidence": "low", "supporting_evidence": ids[:2], "rationale": "r"}]}


def test_one_request_produces_a_report_citing_only_bundle_ids(gen) -> None:
    tools, (observable, _) = _tools(gen, 0)
    ids = [observable.alert.source_id, collect(tools, "full")["logs"][0]["source_id"]]
    client = ScriptedClient([call("submit_report", _valid_report(ids))])
    report = SinglePassInvestigator(client).investigate(tools, observable.scenario_id)
    assert report.stop_reason == "sufficient_evidence" and len(client.requests) == 1
    assert [s.name for s in client.requests[0][1]] == ["submit_report"]  # the only tool offered
    assert client.requests[0][0][0].content == sp.SINGLE_PASS_SYSTEM


def test_unknown_citations_get_one_repair_then_an_error(gen) -> None:
    tools, (observable, _) = _tools(gen, 0)
    good = [observable.alert.source_id, collect(tools, "full")["logs"][0]["source_id"]]
    bad = call("submit_report", _valid_report(["LOG-99999", good[0]]))
    client = ScriptedClient([bad, call("submit_report", _valid_report(good))])
    assert SinglePassInvestigator(client).investigate(tools, observable.scenario_id).stop_reason == "sufficient_evidence"
    assert len(client.requests) == 2 and "LOG-99999" in client.requests[1][0][-1].content
    with pytest.raises(InvestigationFailed) as failed:
        SinglePassInvestigator(ScriptedClient([bad, bad])).investigate(tools, observable.scenario_id)
    assert failed.value.stop_reason == "error" and "after 1 repair" in failed.value.message
    with pytest.raises(InvestigationFailed):
        SinglePassInvestigator(ScriptedClient([text("no tool"), text("still none")])).investigate(
            tools, observable.scenario_id)


def test_provider_caused_errors_stop_at_once_and_others_get_one_retry(gen) -> None:
    tools, (observable, _) = _tools(gen, 0)
    limited = LLMError("http_status", "HTTP 429 after 4 retries", provider_caused=True)
    client = ScriptedClient([limited, call("submit_report", {})])
    with pytest.raises(InvestigationFailed) as failed:
        SinglePassInvestigator(client).investigate(tools, observable.scenario_id)
    assert failed.value.provider_caused and len(client.requests) == 1
    ids = [observable.alert.source_id, collect(tools, "full")["logs"][0]["source_id"]]
    flaky = ScriptedClient([LLMError("timeout", "slow"), call("submit_report", _valid_report(ids))])
    assert SinglePassInvestigator(flaky).investigate(tools, observable.scenario_id).stop_reason == "sufficient_evidence"


def test_reductions_apply_in_order_and_an_unfittable_bundle_is_never_sent(gen) -> None:
    tools, (observable, _) = _tools(gen, 0)
    full_est = SinglePassInvestigator(None)._fitting_request(tools)[1]
    tight = SinglePassInvestigator(None, bounds=replace(AgentBounds(), prompt_budget=full_est - 1))
    messages, estimate, applied = tight._fitting_request(tools)
    assert messages is not None and applied[0] == "message_cap_100" and estimate <= full_est - 1
    client = ScriptedClient([])
    with pytest.raises(InvestigationFailed) as failed:
        SinglePassInvestigator(client, bounds=replace(AgentBounds(), prompt_budget=500)).investigate(
            tools, observable.scenario_id)
    assert failed.value.stop_reason == "context_exhausted" and client.requests == []


def test_the_runner_runs_the_dev_gate_set_originals_only_and_names_its_directory(monkeypatch, tmp_path) -> None:
    from sentinelops.evaluation import single_pass_run

    monkeypatch.setenv("MISTRAL_API_KEY", "mistral_test_key_xyz")
    seen = {}

    def fake(client, backend, model, variant, data_root, out_dir, ids, *args, **kwargs):
        seen.update(dir=out_dir.name, ids=ids, variant=variant, describe=client.describe())
        raise single_pass_run.OutputExists("stop here")

    monkeypatch.setattr(single_pass_run, "run_single_pass", fake)
    for variant in sp.VARIANTS:
        assert single_pass_run.main(["--backend", "mistral", "--model", "ministral-14b-2512", "--rpm", "25",
                                     "--tpm", "750000", "--variant", variant, "--set", "dev-gate",
                                     "--out-root", str(tmp_path)]) == 2
        assert seen["dir"] == f"m5-dev-gate-single-pass-{variant}-mistral-ministral-14b-2512"
        assert seen["ids"] == M5_DEV_SCENARIOS and seen["variant"] == variant
        assert "mistral_test_key_xyz" not in json.dumps(seen["describe"])


def test_run_single_pass_end_to_end_on_a_generated_set(gen, tmp_path) -> None:
    from sentinelops.evaluation.single_pass_run import run_single_pass

    data_root, manifest_dir, scenarios = gen

    class Policy:
        """Cites the alert and the first log in the bundle it was sent."""

        def describe(self):
            return {"backend": "policy"}

        def chat(self, messages, tools):
            ids = sorted(sp._ids("\n".join(m.content for m in messages[1:])))
            log = next(i for i in ids if i.startswith("LOG-"))
            alert = next(i for i in ids if i.startswith("ALR-"))
            return call("submit_report", _valid_report([alert, log]))

    ids = [o.scenario_id for o, _ in scenarios]
    summary = run_single_pass(Policy(), "fake", "policy", "no-timeline", data_root, tmp_path / "out", ids,
                              manifest_dir, stats=lambda p: {"free_disk_gb": 50.0, "swap_used_mb": 0.0,
                                                             "pressure_level": 1})
    assert summary["counts"]["valid_reports"] == len(ids) == summary["counts"]["n"] and summary["counts"]["complete"]
    assert summary["metadata"]["single_pass_sha256"] == FROZEN["no-timeline"] and summary["metadata"]["twins"] is False
    assert all(r["requests"] == 1 for r in summary["runs"])
