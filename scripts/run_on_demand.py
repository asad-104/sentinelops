"""On-demand mechanics run, for the run-agent GitHub workflow or locally. No model, no network, no secrets.

    python scripts/run_on_demand.py --seed 7 --tier standard --fault any --out on-demand [--summary FILE]

Generates one scenario (dev profile, index 0) from the seed, tier and fault, then runs the rule-based baseline and
the state-machine agent driven by a **scripted mock policy** (``DemoAgentPolicy``: not a model, mechanics only),
and scores both against the scenario's ground truth. Before generating anything, the scenario's ID is checked
against the frozen manifests: an ID in the held-out or the fresh-split manifest is refused; a dev ID is allowed.
The check prints yes/no only, never an ID. The summary prints no scenario ID; the artifact folder holds the two
reports, the agent's trace and the summary; the generated scenario files are written to a temporary directory.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from sentinelops.agent.machine import StateMachineInvestigator  # noqa: E402
from sentinelops.agent.mock import DemoAgentPolicy  # noqa: E402
from sentinelops.baselines import INVESTIGATORS  # noqa: E402
from sentinelops.evaluation.harness import CountingToolSet  # noqa: E402
from sentinelops.evaluation.metrics import score_report  # noqa: E402
from sentinelops.llm.trace import TraceWriter  # noqa: E402
from sentinelops.report import InvestigationFailed  # noqa: E402
from sentinelops.scenario_files import dump_json, write_observable  # noqa: E402
from sentinelops.simulator import FaultType, generate_scenario  # noqa: E402
from sentinelops.simulator.datasets import DEFAULT_MANIFEST_DIR  # noqa: E402
from sentinelops.simulator.generator import scenario_id_for  # noqa: E402
from sentinelops.simulator.profiles import DEV_PROFILE, Split, Tier  # noqa: E402
from sentinelops.tools import ToolSet  # noqa: E402

MAX_SEED = 2**31 - 1
INDEX = 0
FAULTS = [f.value for f in FaultType]
LABEL = "Scripted mock policy, not a model: this checks the mechanics, and says nothing about LLM quality."


class Refused(Exception):
    """The requested scenario is in a split the on-demand run must never touch."""


def parse_seed(raw: str) -> int:
    try:
        seed = int(raw.strip(), 10)
    except ValueError:
        raise argparse.ArgumentTypeError("the seed must be a whole number") from None
    if not 0 <= seed <= MAX_SEED:
        raise argparse.ArgumentTypeError(f"the seed must be between 0 and {MAX_SEED}")
    return seed


def membership(seed: int, manifest_dir: Path = DEFAULT_MANIFEST_DIR) -> dict[str, bool]:
    """Whether the scenario this seed would generate is in each frozen manifest (yes/no only; IDs never leave)."""
    sid = scenario_id_for(seed, INDEX)
    out = {}
    for split in (Split.HELDOUT, Split.M5FRESH, Split.DEV):
        path = manifest_dir / f"{split.value}.json"
        if not path.is_file():
            if split is not Split.DEV:  # a missing protected manifest means the check cannot be made: refuse
                raise Refused(f"the {split.value} manifest is missing, so the check cannot be made")
            out[split.value] = False
            continue
        out[split.value] = sid in set(json.loads(path.read_text(encoding="utf-8"))["scenario_ids"])
    return out


def _yes(flag: bool) -> str:
    return "yes" if flag else "no"


def _run(investigator: Any, tools: ToolSet, sid: str) -> tuple[Any, str, str | None, int]:
    counting = CountingToolSet(tools)
    try:
        return investigator.investigate(counting, sid), "sufficient_evidence", None, len(counting.calls)
    except InvestigationFailed as failed:
        return None, failed.stop_reason, failed.message, len(counting.calls)
    except Exception as exc:  # a bug in an investigator is reported, not raised
        return None, "error", f"{type(exc).__name__}: {exc}", len(counting.calls)


def run(seed: int, tier: str, fault: str, out: Path, manifest_dir: Path = DEFAULT_MANIFEST_DIR) -> dict[str, Any]:
    checks = membership(seed, manifest_dir)
    result: dict[str, Any] = {"seed": seed, "tier": tier, "fault_requested": fault, "label": LABEL,
                              "manifest_check": checks}
    if checks[Split.HELDOUT.value] or checks[Split.M5FRESH.value]:
        result["refused"] = True
        return result
    fault_type = FaultType(FAULTS[seed % len(FAULTS)] if fault == "any" else fault)
    observable, truth = generate_scenario(seed, INDEX, fault_type, Tier(tier), DEV_PROFILE)
    sid = observable.scenario_id
    workdir = tempfile.TemporaryDirectory(prefix="sentinelops-on-demand-")
    scenarios = Path(workdir.name)
    write_observable(observable, scenarios / sid)  # observable files only, outside the artifact; truth stays in memory
    arms = {"rule_based": INVESTIGATORS["rule_based"],
            "agent_scripted_mock": StateMachineInvestigator(DemoAgentPolicy(), traces=TraceWriter(out / "traces"),
                                                            prompt_version="v1")}
    result.update(refused=False, fault=fault_type.value,
                  truth={"service": truth.diagnosis.service.value, "fault_type": truth.diagnosis.fault_type.value},
                  arms={})
    for name, investigator in arms.items():
        report, stop, error, calls = _run(investigator, ToolSet.from_directory(scenarios, sid), sid)
        row: dict[str, Any] = {"stop_reason": stop, "report_valid": report is not None, "tool_calls": calls,
                               "error": error}
        if report is not None:
            score = score_report(report, truth, observable)
            dump_json(out / f"report-{name}.json", report.model_dump(mode="json"))
            row.update(top=[{"service": h.service.value, "fault_type": h.fault_type.value,
                             "confidence": h.confidence} for h in report.hypotheses[:3]],
                       top1=score.top1, top3=score.top3, cited=list(report.top.supporting_evidence),
                       headline_valid=score.headline_valid)
        result["arms"][name] = row
    workdir.cleanup()
    return result


def summary_markdown(r: dict[str, Any]) -> str:
    c = r["manifest_check"]
    lines = ["## SentinelOps on-demand run (no model)", "", f"> {r['label']}", "",
             f"Inputs: seed {r['seed']}, tier `{r['tier']}`, fault `{r['fault_requested']}`.", "",
             f"Manifest check: in the held-out manifest **{_yes(c['heldout'])}**; in the fresh-split manifest "
             f"**{_yes(c['m5fresh'])}**; in the dev manifest **{_yes(c['dev'])}**.", ""]
    if r["refused"]:
        lines += ["**Refused:** this seed reproduces a held-out or fresh-split scenario, and those are never run here. "
                  "Choose another seed.", ""]
        return "\n".join(lines)
    t = r["truth"]
    lines += [f"Generated one `{r['tier']}` scenario with the dev profile. Ground truth: **{t['service']} / "
              f"{t['fault_type']}**.", "",
              "| Investigator | Stop | Valid report | Top-1 | Top-3 | Tool calls | Ranked hypotheses (top 3) |",
              "|---|---|---|---|---|---|---|"]
    for name, a in r["arms"].items():
        ranked = "; ".join(f"{h['service']} / {h['fault_type']} ({h['confidence']})" for h in a.get("top", [])) or "–"
        lines.append(f"| {name} | {a['stop_reason']} | {_yes(a['report_valid'])} | "
                     f"{_yes(a.get('top1', False))} | {_yes(a.get('top3', False))} | {a['tool_calls']} | {ranked} |")
    for name, a in r["arms"].items():
        if a.get("cited"):
            lines.append(f"\n{name} top hypothesis cites: " + ", ".join(f"`{i}`" for i in a["cited"][:8]))
        if a["error"]:
            lines.append(f"\n{name} stopped without a valid report: `{a['error'][:200]}`")
    lines += ["", "The artifact holds both reports and the agent's trace. The rule baseline is the M2 baseline (v1); "
              "the agent is the M4 state machine with the frozen v1 prompt, driven by a scripted policy."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/run_on_demand.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--seed", type=parse_seed, required=True)
    parser.add_argument("--tier", choices=[t.value for t in Tier], default=Tier.STANDARD.value)
    parser.add_argument("--fault", choices=["any", *FAULTS], default="any")
    parser.add_argument("--out", type=Path, default=Path("on-demand"))
    parser.add_argument("--summary", type=Path, help="append the Markdown summary here (the workflow's job summary)")
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        result = run(args.seed, args.tier, args.fault, args.out, args.manifest_dir)
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    text = summary_markdown(result)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.md").write_text(text, encoding="utf-8")
    dump_json(args.out / "result.json", result)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as f:
            f.write(text)
    print(text)
    return 2 if result["refused"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
