"""M4 agent CLI: fixed set, mock refusals (core scenarios, eval/agent/), mock end to end on a generated set,
no overwrite, summary on abort, no secrets, frozen prompt. No model, no network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_sets import generated_set
from sentinelops.agent.mock import DemoAgentPolicy
from sentinelops.agent.prompt import SYSTEM_PROMPT, prompt_sha256
from sentinelops.evaluation import agent_run
from sentinelops.evaluation.agent_run import (
    CORE_SCENARIOS,
    REAL_RESULTS,
    Refused,
    check_mock_target,
    main,
    run_agent,
)
from sentinelops.evaluation.harness import HarnessAbort
from sentinelops.evaluation.pilot import PILOT_SCENARIOS, OutputExists
from sentinelops.simulator.datasets import build_split, manifest_path
from sentinelops.simulator.profiles import Split

PREREGISTERED_CORE = ("sc-30385ffc64", "sc-3836c69ef7", "sc-3e3ceb314e", "sc-4001bf784c", "sc-408b514aeb",
                      "sc-4251e8920a", "sc-497fd61898", "sc-5b55b772de", "sc-5c5b9b9197", "sc-91404ea5fc")
# Frozen 2026-10-23 in stage A; a change needs a logged prompt revision in docs/PROGRESS.md first.
# Revision 1 (2026-10-27, smoke run 1): reply-only rule, /no_think, STAGE template hashed with progress lines.
FROZEN_AGENT_PROMPT_SHA256 = "d269d28d9581a9d931c936c333259de648526a3970de99b952e0011fe2b2e9eb"  # revision 2


def _calm(path: Path) -> dict:
    return {"free_disk_gb": 50.0, "swap_used_mb": 100.0, "pressure_level": 1}


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory):
    return generated_set(tmp_path_factory.mktemp("agentset"))


def test_core_set_is_the_preregistered_one() -> None:
    assert CORE_SCENARIOS == PREREGISTERED_CORE


def test_core_set_follows_its_selection_rule() -> None:
    scenarios = build_split(Split.DEV)
    truth = {o.scenario_id: t for o, t in scenarios}
    order = sorted(truth)  # the manifest lists IDs sorted
    excluded = set(PILOT_SCENARIOS) | {"sc-2c422896a9"}
    picked, per = [], {}
    for sid in order:
        fault = truth[sid].diagnosis.fault_type.value
        if sid not in excluded and per.get(fault, 0) < 2:
            per[fault] = per.get(fault, 0) + 1
            picked.append(sid)
    assert tuple(picked) == CORE_SCENARIOS
    tiers = [truth[s].tier.value for s in CORE_SCENARIOS]
    assert (tiers.count("standard"), tiers.count("ambiguous"), tiers.count("missing_evidence")) == (5, 2, 3)
    assert sorted(s for s in CORE_SCENARIOS if truth[s].injection) == ["sc-5b55b772de", "sc-5c5b9b9197"]


def test_mock_refuses_core_scenarios_and_the_real_results_directory(tmp_path: Path) -> None:
    with pytest.raises(Refused, match="core"):
        check_mock_target([CORE_SCENARIOS[0]], tmp_path / "out")
    with pytest.raises(Refused, match="eval/agent"):
        check_mock_target(["sc-0000000001"], REAL_RESULTS / "generator-v5" / "mock-scripted")
    assert not (REAL_RESULTS / "generator-v5" / "mock-scripted").exists()


def test_mock_cli_refuses_the_real_dev_manifest_and_the_default_output(generated, tmp_path: Path) -> None:
    from conftest import REPO_ROOT

    real_manifest = REPO_ROOT / "eval" / "manifests"
    assert main(["--backend", "mock", "--manifest-dir", str(real_manifest), "--out-root", str(tmp_path / "never-used"),
                 "--quiet"]) == 2  # the real dev manifest contains the core scenarios
    data_root, manifest_dir, _ = generated
    assert main(["--backend", "mock", "--data-root", str(data_root), "--manifest-dir", str(manifest_dir),
                 "--quiet"]) == 2  # default --out-root is eval/agent/
    assert not any(p.name.startswith("mock-") for p in REAL_RESULTS.glob("*/*"))  # no mock output under eval/agent/


def test_mock_runs_end_to_end_on_a_generated_set(generated, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_root, manifest_dir, scenarios = generated
    monkeypatch.setattr(agent_run, "system_stats", _calm)
    secret = "sk-test-DO-NOT-LEAK-0123456789"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)
    assert main(["--backend", "mock", "--data-root", str(data_root), "--manifest-dir", str(manifest_dir),
                 "--out-root", str(tmp_path), "--quiet"]) == 0
    out = tmp_path / "generator-v5" / "mock-scripted"
    summary = json.loads((out / "summary.json").read_text())
    twins = sum(t.injection is not None for _, t in scenarios)
    assert len(summary["runs"]) == len(scenarios) + twins
    assert summary["rule"]["verdict"] == "not applicable (mock backend)"
    assert summary["rule"]["budgets"] == {"agent": 40, "rule_baseline": 52}
    assert all(r["stop_reason"] == "sufficient_evidence" for r in summary["runs"])
    assert all(r["investigated"] for r in summary["runs"])  # the scripted policy is built to satisfy (a)-(f)
    assert "process, not insight" in (out / "summary.md").read_text()
    assert not any(secret in p.read_text() for p in out.rglob("*") if p.is_file())


def test_existing_attempts_are_never_overwritten(generated, tmp_path: Path) -> None:
    data_root, manifest_dir, scenarios = generated
    ids = [o.scenario_id for o, _ in scenarios]
    (tmp_path / "traces").mkdir()
    (tmp_path / "traces" / "01-sc-0000000001.jsonl").write_text("{}\n")
    with pytest.raises(OutputExists):
        run_agent(DemoAgentPolicy(), "mock", "scripted", data_root, tmp_path, ids, manifest_dir, stats=_calm)


def test_an_aborted_batch_writes_a_summary_marked_incomplete(generated, tmp_path: Path) -> None:
    data_root, manifest_dir, scenarios = generated
    ids = [o.scenario_id for o, _ in scenarios]
    readings = iter([_calm(tmp_path)] * 3)
    with pytest.raises(HarnessAbort):
        run_agent(DemoAgentPolicy(), "fake", "scripted", data_root, tmp_path, ids, manifest_dir,
                  stats=lambda p: next(readings, {"free_disk_gb": 5.0, "swap_used_mb": 100.0, "pressure_level": 1}),
                  attempt=2)
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["metadata"]["aborted"] and summary["rule"]["complete"] is False
    assert summary["rule"]["verdict"] == "propose_hosted"


def test_agent_prompt_is_frozen() -> None:
    assert prompt_sha256() == FROZEN_AGENT_PROMPT_SHA256, "agent prompt changed: log a revision first"
    assert "untrusted data" in SYSTEM_PROMPT


def test_changing_the_stage_template_changes_the_prompt_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    from sentinelops.agent import prompt

    before = prompt.prompt_sha256()
    monkeypatch.setitem(prompt.STAGE_TEMPLATE, "reply", "Reply with two tool calls.")
    assert prompt.prompt_sha256() != before


@pytest.mark.parametrize("table", ["DATA_HEADERS", "HARNESS_NOTES", "HARNESS_MESSAGES"])
def test_changing_any_harness_text_changes_the_prompt_hash(monkeypatch: pytest.MonkeyPatch, table: str) -> None:
    from sentinelops.agent import prompt

    before = prompt.prompt_sha256()
    for key, value in getattr(prompt, table).items():
        with monkeypatch.context() as m:
            m.setitem(getattr(prompt, table), key, value + " ")
            assert prompt.prompt_sha256() != before, f"{table}[{key!r}] is not covered by the hash"


def test_the_loop_sends_no_inline_text_to_the_model() -> None:
    """Notes, rejections, acceptances and DATA headers must come from agent/prompt.py (revision 2)."""
    import ast

    import sentinelops.agent.context as context
    import sentinelops.agent.machine as machine

    def literal(node: ast.AST) -> bool:
        return isinstance(node, ast.JoinedStr) or (isinstance(node, ast.Constant) and isinstance(node.value, str))

    offenders = []
    for module in (machine, context):
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                name, args = node.func.attr, node.args
                message = (args[0] if name == "append" and ast.unparse(node.func.value) == "self.notes" else
                           args[2] if name == "reject" and len(args) > 2 else
                           args[1] if name == "accept" and len(args) > 1 else None)
                if message is not None and literal(message):
                    offenders.append(f"{module.__name__}:{node.lineno}")
            if isinstance(node, ast.List) and node.elts and literal(node.elts[0]):
                text = node.elts[0].value if isinstance(node.elts[0], ast.Constant) else ""
                if text.startswith("DATA"):
                    offenders.append(f"{module.__name__}:{node.lineno}")
    assert offenders == []


def test_stage_block_shows_precondition_progress_and_the_reply_rule() -> None:
    from sentinelops.agent.context import ContextBuilder
    from sentinelops.agent.prompt import STATE_INSTRUCTIONS
    from sentinelops.agent.schemas import agent_tool_specs
    from sentinelops.agent.states import AgentBounds, State

    builder = ContextBuilder(AgentBounds(), agent_tool_specs())
    gather = builder.stage_block(State.GATHER, STATE_INSTRUCTIONS[State.GATHER], 5, ["n"], {"evidence": 1, "verify": 0})
    assert gather.splitlines()[0] == "STAGE (from the harness): GATHER"
    assert "Evidence calls so far on this GATHER pass: 1" in gather and "finish_gathering needs 4" in gather
    assert gather.splitlines()[-1] == "Reply with one tool call only." and "Note from the harness: n" in gather
    verify = builder.stage_block(State.VERIFY, STATE_INSTRUCTIONS[State.VERIFY], 9, [], {"evidence": 4, "verify": 2})
    assert "VERIFY read calls so far: 2 of 8; finish_verifying needs at least 1." in verify
    assert "Evidence calls" not in verify


def test_a_provider_caused_stop_aborts_the_batch_as_incomplete(generated, tmp_path: Path) -> None:
    """Pre-registered 2026-10-29: a provider limit or outage ends the batch (HarnessAbort), it does not turn
    every remaining run into an error row. The stopped run's own trace and row are kept."""
    from sentinelops.llm.client import LLMError

    class LimitedClient:
        def __init__(self) -> None:
            self.calls = 0

        def describe(self):
            return {"backend": "limited"}

        def chat(self, messages, tools):
            self.calls += 1
            return LLMError("http_status", "HTTP 429: provider asks to wait 445 s", provider_caused=True)

    data_root, manifest_dir, scenarios = generated
    ids = [o.scenario_id for o, _ in scenarios]
    client = LimitedClient()
    with pytest.raises(HarnessAbort) as aborted:
        run_agent(client, "fake", "limited", data_root, tmp_path, ids, manifest_dir, stats=_calm)
    assert "provider-caused stop" in str(aborted.value) and client.calls == 1  # the next run never started
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["metadata"]["aborted"] and summary["rule"]["complete"] is False
    assert len(summary["runs"]) == 1 and summary["runs"][0]["stop_reason"] == "error"
    log = [json.loads(line) for line in (tmp_path / "run_log.jsonl").read_text().splitlines()]
    assert [e["event"] for e in log] == ["batch_start", "run_start", "abort", "run_end"]


@pytest.mark.parametrize("backend", ["mistral", "groq"])
def test_hosted_backends_receive_only_dev_data(generated, tmp_path: Path, backend: str) -> None:
    """Data rule, enforced in code (2026-10-29): no held-out root, no scenario outside the dev manifest."""
    from sentinelops.evaluation.agent_run import Refused

    data_root, manifest_dir, scenarios = generated
    ids = [o.scenario_id for o, _ in scenarios]
    heldout_root = tmp_path / "data" / "heldout"
    heldout_root.mkdir(parents=True)
    with pytest.raises(Refused, match="held-out"):
        run_agent(DemoAgentPolicy(), backend, "m", heldout_root, tmp_path / "o1", ids, manifest_dir, stats=_calm)
    with pytest.raises(Refused, match="dev scenarios only"):
        run_agent(DemoAgentPolicy(), backend, "m", data_root, tmp_path / "o2", [*ids[:1], "sc-ffffffffff"],
                  manifest_dir, stats=_calm)
    assert not (tmp_path / "o1").exists() and not (tmp_path / "o2").exists()  # refused before anything ran
