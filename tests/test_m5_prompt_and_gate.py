"""M5 stage B: the v2 prompt (frozen hash, approved wording, tool names), its wiring through the agent and the CLI,
originals-only runs, and the dev gate report's rules. Offline; no model."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from agent_sets import generated_set
from conftest import REPO_ROOT
from sentinelops.agent.machine import StateMachineInvestigator
from sentinelops.agent.prompt import GATHER_V2, STATE_INSTRUCTIONS, prompt_sha256, state_instructions
from sentinelops.agent.schemas import agent_tool_specs
from sentinelops.agent.states import State
from sentinelops.evaluation import agent_run, m5_gate
from sentinelops.evaluation.agent_run import CORE_SCENARIOS, M3_SMOKE_SCENARIO, M4_SMOKE_SCENARIO, M5_DEV_SCENARIOS
from sentinelops.evaluation.harness import CountingToolSet
from sentinelops.evaluation.pilot import PILOT_SCENARIOS
from sentinelops.llm.mock import ScriptedClient, call
from sentinelops.tools import ToolSet

FROZEN_V2_SHA256 = "0a788479eb8cb380f7fd737932e52f28c96d9463e250c6722ccbe31d91d7fc30"


def test_v2_hash_is_frozen_and_v1_is_unchanged() -> None:
    assert prompt_sha256("v2") == FROZEN_V2_SHA256
    assert prompt_sha256("v1") == prompt_sha256() == "d269d28d9581a9d931c936c333259de648526a3970de99b952e0011fe2b2e9eb"
    with pytest.raises(ValueError):
        state_instructions("v3")


def test_v2_changes_only_the_gather_instruction_and_matches_the_approved_wording() -> None:
    v2 = state_instructions("v2")
    assert {s for s in State if v2.get(s) != STATE_INSTRUCTIONS.get(s)} == {State.GATHER}
    doc = (REPO_ROOT / "docs/m5_v2_and_single_pass.md").read_text(encoding="utf-8")
    approved = re.search(r"\*\*v2 \(exact, 681 characters\):\*\*\n\n> (.+)\n", doc).group(1)
    assert GATHER_V2 == approved and len(GATHER_V2) == 681


def test_v2_names_only_real_tools() -> None:
    identifiers = set(re.findall(r"\b[a-z]+(?:_[a-z]+)+\b", GATHER_V2))
    assert identifiers == {"get_timeline", "list_deployments", "list_config_changes", "finish_gathering"}
    assert identifiers <= {s.name for s in agent_tool_specs()}


def test_the_agent_sends_the_v2_instruction_and_records_its_version(toolset: ToolSet, tmp_path: Path) -> None:
    from sentinelops.llm.trace import TraceWriter

    sid = toolset.call("get_window").items[0].scenario_id
    for version in ("v1", "v2"):
        client = ScriptedClient([call("search_logs", {"limit": 1})])
        agent = StateMachineInvestigator(client, prompt_version=version, traces=TraceWriter(tmp_path / version))
        with pytest.raises(Exception):
            agent.investigate(CountingToolSet(toolset), sid)
        stage = client.requests[0][0][-1].content
        assert (GATHER_V2 in stage) == (version == "v2")
        assert (STATE_INSTRUCTIONS[State.GATHER] in stage) == (version == "v1")
        start = json.loads(next((tmp_path / version).glob("*.jsonl")).read_text().splitlines()[0])
        assert start["prompt_version"] == version and start["prompt_sha256"] == prompt_sha256(version)


def test_the_dev_gate_set_is_the_preregistered_22_and_uses_nothing_already_used() -> None:
    doc = (REPO_ROOT / "docs/m5_preregistration.md").read_text(encoding="utf-8")
    table = doc[doc.index("## 2. Development scenarios"):doc.index("## 3.")]
    assert tuple(re.findall(r"^\| `(sc-[0-9a-f]{10})` \|", table, flags=re.M)) == M5_DEV_SCENARIOS
    assert len(set(M5_DEV_SCENARIOS)) == 22
    assert not set(M5_DEV_SCENARIOS) & {*CORE_SCENARIOS, *PILOT_SCENARIOS, M3_SMOKE_SCENARIO, M4_SMOKE_SCENARIO}
    dev = json.loads((REPO_ROOT / "eval/manifests/dev.json").read_text())["scenario_ids"]
    assert set(M5_DEV_SCENARIOS) <= set(dev)


def test_cli_dev_gate_runs_names_and_options(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MISTRAL_API_KEY", "mistral_test_key_xyz")
    captured: dict = {}

    def fake_run_agent(client, backend, model, data_root, out_dir, ids, *args, **kwargs):
        captured.setdefault("runs", []).append((out_dir.name, ids, kwargs["prompt_version"], kwargs["twins"]))
        raise agent_run.OutputExists("stop here")

    monkeypatch.setattr(agent_run, "run_agent", fake_run_agent)
    for prompt in ("v1", "v2"):
        agent_run.main(["--backend", "mistral", "--model", "ministral-14b-2512", "--rpm", "25", "--tpm", "750000",
                        "--set", "dev-gate", "--prompt", prompt, "--no-twins", "--quiet", "--out-root", str(tmp_path)])
    assert captured["runs"] == [
        ("m5-dev-gate-mistral-ministral-14b-2512-prompt-v1", M5_DEV_SCENARIOS, "v1", False),
        ("m5-dev-gate-mistral-ministral-14b-2512-prompt-v2", M5_DEV_SCENARIOS, "v2", False)]
    captured.clear()
    agent_run.main(["--backend", "mistral", "--model", "ministral-14b-2512", "--rpm", "25", "--tpm", "750000",
                    "--quiet", "--out-root", str(tmp_path)])
    assert captured["runs"] == [("mistral-ministral-14b-2512", CORE_SCENARIOS, "v1", True)]  # M4 naming unchanged


def test_run_agent_without_twins_runs_originals_only(tmp_path: Path) -> None:
    from sentinelops.agent.mock import DemoAgentPolicy

    data_root, manifest_dir, scenarios = generated_set(tmp_path / "set")
    ids = [o.scenario_id for o, _ in scenarios]
    injected = sum(g.injection is not None for _, g in scenarios)
    assert injected  # the generated set has injection twins to skip
    calm = lambda p: {"free_disk_gb": 50.0, "swap_used_mb": 0.0, "pressure_level": 1}
    summary = agent_run.run_agent(DemoAgentPolicy(), "mock", "scripted", data_root, tmp_path / "out", ids,
                                  manifest_dir, stats=calm, twins=False)
    assert len(summary["runs"]) == len(ids) and all(r["variant"] == "original" for r in summary["runs"])
    assert summary["metadata"]["twins"] is False and summary["rule"]["complete"]


# ---- the dev gate report

def _write_arm(root: Path, version: str, runs: list[list[dict]], valid: list[bool], aborted: str | None = None,
               ids=M5_DEV_SCENARIOS) -> Path:
    (root / "traces").mkdir(parents=True)
    rows = []
    for i, (sid, events) in enumerate(zip(ids, runs), 1):
        name = f"{i:02d}-{sid}.jsonl"
        (root / "traces" / name).write_text("".join(json.dumps(e) + "\n" for e in events))
        rows.append({"scenario_id": sid, "trace": name, "report_valid": valid[i - 1], "top1": i % 2 == 0,
                     "investigated_f_no_overflow": True})
    (root / "summary.json").write_text(json.dumps({"metadata": {"prompt_sha256": prompt_sha256(version),
                                                                "prompt_version": version, "aborted": aborted},
                                                   "runs": rows}))
    return root


def _tool(name, records=1, ok=True, code=None):
    return {"event": "tool", "by_loop": False, "name": name, "ok": ok, "error_code": code,
            "records": [{"id": f"X-{i}"} for i in range(records)]}


def _run(*tools, levels=(0, 3), stop="sufficient_evidence"):
    ctx = [{"event": "context", "state": s, "level": lv} for s, lv in zip(("GATHER", "HYPOTHESIZE"), levels)]
    return [*ctx, *tools, {"event": "stop", "stop_reason": stop}]


def test_valid_change_call_needs_records_and_must_come_before_the_first_ranking() -> None:
    assert m5_gate.run_facts(_run(_tool("get_timeline"), _tool("submit_hypotheses", 0)))["valid_change_call"]
    assert not m5_gate.run_facts(_run(_tool("get_timeline", records=0), _tool("submit_hypotheses", 0)))["valid_change_call"]
    assert not m5_gate.run_facts(_run(_tool("submit_hypotheses", 0), _tool("list_deployments")))["valid_change_call"]
    assert not m5_gate.run_facts(_run(_tool("list_config_changes", ok=False, code="invalid_arguments")))["valid_change_call"]
    facts = m5_gate.run_facts(_run(_tool("get_config_changes", 0, ok=False, code="unknown_tool")))
    assert facts["unknown_tool_calls"] == 1 and not facts["valid_change_call"]


def test_the_gate_passes_fails_and_is_incomplete_by_the_preregistered_rules(tmp_path: Path) -> None:
    plain = _run(_tool("search_logs"), _tool("submit_hypotheses", 0))
    checked = _run(_tool("get_timeline"), _tool("search_logs"), _tool("submit_hypotheses", 0), levels=(0, 1))
    v1 = _write_arm(tmp_path / "v1", "v1", [plain] * 22, [True] * 20 + [False] * 2)
    v2 = _write_arm(tmp_path / "v2", "v2", [checked] * 16 + [plain] * 6, [True] * 20 + [False] * 2)
    g = m5_gate.gate(v1, v2)
    assert g["passed"] and g["checks"] == {"G1": True, "G2": True, "G3": True, "G4": True}
    assert g["v2"]["levels_hypothesize"] == {1: 16, 3: 6} and g["v1"]["top1"] == 11  # information only
    text = m5_gate.report_markdown(g)
    assert "Gate: PASSED" in text and "not a result" in text and "16/22" in text

    v2_15 = _write_arm(tmp_path / "v2b", "v2", [checked] * 15 + [plain] * 7, [True] * 20 + [False] * 2)
    assert not m5_gate.gate(v1, v2_15)["checks"]["G1"]  # 15 of 22 is below the threshold
    v2_reg = _write_arm(tmp_path / "v2c", "v2", [checked] * 22, [True] * 19 + [False] * 3)
    assert not m5_gate.gate(v1, v2_reg)["checks"]["G2"]  # fewer valid reports than v1
    unknown = _run(_tool("get_timeline"), _tool("get_config_changes", 0, ok=False, code="unknown_tool"),
                   _tool("submit_hypotheses", 0))
    v2_unk = _write_arm(tmp_path / "v2d", "v2", [checked] * 21 + [unknown], [True] * 22)
    assert not m5_gate.gate(v1, v2_unk)["checks"]["G3"]
    v2_ovf = _write_arm(tmp_path / "v2e", "v2", [checked] * 21 + [_run(stop="context_exhausted")], [True] * 22)
    assert not m5_gate.gate(v1, v2_ovf)["checks"]["G4"]
    short = _write_arm(tmp_path / "v2f", "v2", [checked] * 21, [True] * 21, ids=M5_DEV_SCENARIOS[:21])
    g = m5_gate.gate(v1, short)
    assert not g["complete"] and not g["passed"] and "INCOMPLETE" in m5_gate.report_markdown(g)
    aborted = _write_arm(tmp_path / "v2g", "v2", [checked] * 22, [True] * 22, aborted="provider-caused stop")
    assert not m5_gate.gate(v1, aborted)["passed"]
