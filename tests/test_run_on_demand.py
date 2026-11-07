"""The on-demand run (scripts/run_on_demand.py and .github/workflows/run-agent.yml). Offline: the network guard is on,
and the manifest checks use stand-in manifests, never the real held-out or fresh-split data."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

from conftest import REPO_ROOT
from sentinelops.simulator.generator import scenario_id_for

spec = importlib.util.spec_from_file_location("run_on_demand", REPO_ROOT / "scripts" / "run_on_demand.py")
od = importlib.util.module_from_spec(spec)
spec.loader.exec_module(od)

HELD, FRESH, DEV, FREE = 11, 22, 33, 44  # seeds placed in stand-in manifests; FREE is in none
ANY_ID = re.compile(r"sc-[0-9a-f]{10}")


@pytest.fixture()
def manifests(tmp_path: Path) -> Path:
    for split, seed in (("heldout", HELD), ("m5fresh", FRESH), ("dev", DEV)):
        (tmp_path / f"{split}.json").write_text(json.dumps({"scenario_ids": [scenario_id_for(seed, od.INDEX)]}))
    return tmp_path


def test_membership_is_yes_or_no_per_manifest(manifests: Path) -> None:
    assert od.membership(HELD, manifests) == {"heldout": True, "m5fresh": False, "dev": False}
    assert od.membership(FRESH, manifests) == {"heldout": False, "m5fresh": True, "dev": False}
    assert od.membership(DEV, manifests) == {"heldout": False, "m5fresh": False, "dev": True}
    assert od.membership(FREE, manifests) == {"heldout": False, "m5fresh": False, "dev": False}


@pytest.mark.parametrize("seed", [HELD, FRESH])
def test_held_out_and_fresh_split_scenarios_are_refused_before_generation(seed: int, manifests: Path, tmp_path: Path,
                                                                           capsys) -> None:
    out = tmp_path / "out"
    assert od.main(["--seed", str(seed), "--out", str(out), "--manifest-dir", str(manifests)]) == 2
    printed = capsys.readouterr().out
    assert "**Refused:**" in printed and "**yes**" in printed
    assert not (out / "traces").exists() and not list(out.glob("report-*.json"))  # nothing was generated or run
    for text in (printed, (out / "summary.md").read_text(), (out / "result.json").read_text()):
        assert not ANY_ID.search(text)


def test_a_dev_scenario_is_allowed(manifests: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    assert od.main(["--seed", str(DEV), "--out", str(out), "--manifest-dir", str(manifests)]) == 0
    assert "in the dev manifest **yes**" in (out / "summary.md").read_text()


def test_a_missing_protected_manifest_refuses(manifests: Path, tmp_path: Path) -> None:
    (manifests / "m5fresh.json").unlink()
    assert od.main(["--seed", str(FREE), "--out", str(tmp_path / "out"), "--manifest-dir", str(manifests)]) == 2


@pytest.mark.parametrize("bad", ["-1", "2147483648", "abc", "1.5", "1e3", "", " ", "7; rm -rf /"])
def test_invalid_seeds_are_rejected(bad: str, tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        od.main(["--seed", bad, "--out", str(tmp_path / "out")])
    assert exc.value.code == 2 and not (tmp_path / "out").exists()


def test_tier_and_fault_must_be_from_the_lists(tmp_path: Path) -> None:
    for args in (["--tier", "heldout"], ["--fault", "disk_full"]):
        with pytest.raises(SystemExit):
            od.main(["--seed", "7", "--out", str(tmp_path / "out"), *args])


def test_an_end_to_end_run_scores_both_arms_and_is_labelled(manifests: Path, tmp_path: Path) -> None:
    out, summary = tmp_path / "out", tmp_path / "job-summary.md"
    assert od.main(["--seed", str(FREE), "--tier", "ambiguous", "--fault", "config_error", "--out", str(out),
                    "--summary", str(summary), "--manifest-dir", str(manifests)]) == 0
    result = json.loads((out / "result.json").read_text())
    assert result["truth"]["fault_type"] == "config_error" and set(result["arms"]) == {"rule_based",
                                                                                       "agent_scripted_mock"}
    assert all(isinstance(a["tool_calls"], int) and a["stop_reason"] for a in result["arms"].values())
    text = summary.read_text()
    assert "Scripted mock policy, not a model" in text and "says nothing about LLM quality" in text
    assert not ANY_ID.search(text)  # the summary never names the scenario
    assert {p.name for p in out.iterdir()} >= {"summary.md", "result.json", "traces"}
    assert not any(p.is_dir() and p.name == "scenario" for p in out.iterdir())  # scenario files stay out of the artifact


WORKFLOWS = REPO_ROOT / ".github" / "workflows"
SECRETS = re.compile(r"\$\{\{\s*secrets\.")


def test_the_workflow_passes_inputs_only_through_env() -> None:
    text = (WORKFLOWS / "run-agent.yml").read_text()
    uses = [line.strip() for line in text.splitlines() if "${{ inputs." in line]
    assert uses and all(re.fullmatch(r"[A-Z_]+: \$\{\{ inputs\.[a-z_]+ \}\}", u) for u in uses), uses
    assert "workflow_dispatch:" in text and "push:" not in text and "pull_request" not in text
    assert "contents: read" in text and not SECRETS.search(text)


@pytest.mark.parametrize("name", ["ci.yml", "run-agent.yml"])
def test_workflows_pin_actions_by_commit_and_use_no_secrets(name: str) -> None:
    text = (WORKFLOWS / name).read_text()
    uses = re.findall(r"uses: (\S+)", text)
    assert uses and all(re.fullmatch(r"actions/[a-z-]+@[0-9a-f]{40}", u) for u in uses), uses
    assert "permissions:\n  contents: read" in text and not SECRETS.search(text)
    assert "persist-credentials: false" in text
