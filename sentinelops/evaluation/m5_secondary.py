"""M5 secondary measures (docs/m5_preregistration.md section 7), per arm, from committed outputs. No model call.

Built after the fresh-split runs and before the fresh analysis was run; developed and checked on the M5 dev-gate
outputs only (``python -m sentinelops.evaluation.m5_secondary --dir <dev-gate dir> --data-root data/dev``).

Per run, rebuilt from the trace and the scenario's files (the same scoring the harness uses, ``score_report``):
  evidence validity  top-1 citations in the headline / strict / lenient relevant sets (pooled counts, no interval:
                     citations within a run are correlated); fabricated citations
  unsupported claims hypotheses citing no existing ID, over all hypotheses
  investigated       (a)-(f) as pre-registered for M4 (``agent_metrics.investigated``); agent only
  tool calls         the agent's calls including the 3 loop-issued TRIAGE calls, against its budget of 40 and the
                     rule baseline's about 52; single-pass makes no tool calls (its bundle is built by a fixed rule)
  times              wall (elapsed) and active (elapsed minus provider rate-limit waits), median and max
  change tool        a valid change-tool call (G1 definition: returns a record, before the first ranking); agent only
  trigger seen       the trigger record's ID was shown to the model: for the agent, among the IDs a tool result
                     showed it (inside the result cap); for single-pass, in the bundle rebuilt from the data with the
                     frozen rule. Over runs whose scenario has a trigger record
A run without a valid report cites nothing (as the harness's error rows). Hosted times are not evidence of quality.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from sentinelops.agent.single_pass import SinglePassInvestigator, _ids
from sentinelops.evaluation.agent_metrics import investigated
from sentinelops.evaluation.m5_gate import run_facts
from sentinelops.evaluation.metrics import ScenarioScore, score_report, wilson
from sentinelops.llm.trace import read_trace
from sentinelops.models import ScenarioObservable
from sentinelops.report import InvestigationReport
from sentinelops.scenario_files import load_observable
from sentinelops.simulator.ground_truth import GroundTruth
from sentinelops.tools import ToolSet

AGENT_BUDGET, RULE_BASELINE_CALLS = 40, "about 52"
INVESTIGATED_PARTS = ("a_valid_report", "b_gather_evidence_calls", "c_data_kinds", "d_top_supported", "e_verified",
                      "f_no_overflow", "investigated")


def existing_ids(observable: ScenarioObservable) -> set[str]:
    out = {observable.alert.source_id}
    for records in (observable.logs, observable.metrics, observable.deployments, observable.config_changes,
                    observable.dependencies):
        out.update(r.source_id for r in records)
    return out


def agent_shown(events: list[dict[str, Any]]) -> set[str]:
    """Every ID a tool result showed the agent (loop-issued calls included; inside the result cap)."""
    return {i for e in events if e["event"] == "tool" for i in e.get("new_ids") or []}


@lru_cache(maxsize=512)
def _bundle(scenarios_dir: str, scenario_id: str, variant: str) -> frozenset[str]:
    messages, _, _ = SinglePassInvestigator(None, variant=variant)._fitting_request(
        ToolSet.from_directory(Path(scenarios_dir), scenario_id))
    return frozenset(_ids("\n".join(m.content for m in (messages or [])[1:])))


def bundle_ids(data_root: Path, scenario_id: str, variant: str) -> set[str]:
    """The IDs in the single-pass bundle, rebuilt from the data with the frozen rule (independent of the model)."""
    return set(_bundle(str(data_root / "scenarios"), scenario_id, variant))


def _citations(report: InvestigationReport | None, truth: GroundTruth,
               observable: ScenarioObservable) -> dict[str, int]:
    if report is None:
        return dict(cited=0, headline_valid=0, strict_valid=0, lenient_valid=0, fabricated=0, hypotheses=0,
                    unsupported=0)
    s = score_report(report, truth, observable)
    return dict(cited=s.cited, headline_valid=s.headline_valid, strict_valid=s.strict_valid,
                lenient_valid=s.lenient_valid, fabricated=s.fabricated, hypotheses=s.hypotheses,
                unsupported=s.unsupported)


def run_measures(kind: str, row: dict[str, Any], events: list[dict[str, Any]], truth: GroundTruth,
                 observable: ScenarioObservable, shown: set[str], num_ctx: int | None = None) -> dict[str, Any]:
    """One hosted run. ``kind`` is "agent" or "single_pass"; ``shown`` is the set of IDs the model was shown."""
    stop = next((e for e in events if e["event"] == "stop"), None)
    report = (InvestigationReport.model_validate(stop["report"])
              if row["report_valid"] and stop and stop.get("report") else None)
    wait = sum(e.get("wait_s") or 0.0 for e in events if e["event"] == "model")
    elapsed = stop.get("elapsed_s") if stop else None
    out: dict[str, Any] = {
        "scenario_id": row["scenario_id"], "valid": report is not None, **_citations(report, truth, observable),
        "wall_s": elapsed, "active_s": (stop.get("active_s", elapsed - wait) if elapsed is not None else None),
        "has_trigger": truth.trigger_source_id is not None,
        "trigger_seen": truth.trigger_source_id is not None and truth.trigger_source_id in shown,
    }
    if kind == "agent":
        out["tool_calls"] = stop.get("tool_calls") if stop else None
        out["valid_change_call"] = run_facts(events)["valid_change_call"]
        parts = investigated(events, existing_ids(observable), num_ctx or 0)
        out.update({k: bool(parts[k]) for k in INVESTIGATED_PARTS})
    return out


def local_measures(score: ScenarioScore) -> dict[str, Any]:
    """One local baseline run, from the harness's own score (no trace, no notion of what was shown)."""
    return {"scenario_id": score.scenario_id, "valid": score.report_valid, "cited": score.cited,
            "headline_valid": score.headline_valid, "strict_valid": score.strict_valid,
            "lenient_valid": score.lenient_valid, "fabricated": score.fabricated, "hypotheses": score.hypotheses,
            "unsupported": score.unsupported, "tool_calls": score.tool_calls, "wall_s": score.duration_s,
            "active_s": score.duration_s}


def _share(rows: Sequence[dict[str, Any]], key: str, among: str | None = None) -> dict[str, Any]:
    base = [r for r in rows if among is None or r[among]]
    k, n = sum(bool(r[key]) for r in base), len(base)
    low, high = wilson(k, n)
    return {"k": k, "n": n, "wilson_95": [round(low, 4), round(high, 4)]}


def _spread(values: Sequence[float | int | None]) -> dict[str, Any]:
    xs = sorted(v for v in values if v is not None)
    return {"n": len(xs), "median": statistics.median(xs) if xs else None, "max": xs[-1] if xs else None,
            "min": xs[0] if xs else None}


def aggregate(kind: str, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """One arm's secondary measures. ``kind`` is "agent", "single_pass" or "local"; inapplicable measures are None."""
    cited = sum(r["cited"] for r in rows)

    def pool(key: str) -> dict[str, Any]:
        k = sum(r[key] for r in rows)
        return {"k": k, "n": cited, "pct": round(100 * k / cited, 1) if cited else None}

    return {
        "runs": len(rows),
        "evidence_headline": pool("headline_valid"), "evidence_strict": pool("strict_valid"),
        "evidence_lenient": pool("lenient_valid"),
        "fabricated_citations": sum(r["fabricated"] for r in rows),
        "unsupported_hypotheses": {"k": sum(r["unsupported"] for r in rows), "n": sum(r["hypotheses"] for r in rows)},
        "investigated": {p: _share(rows, p) for p in INVESTIGATED_PARTS} if kind == "agent" else None,
        "tool_calls": _spread([r["tool_calls"] for r in rows]) if kind != "single_pass" else None,
        "wall_s": _spread([r["wall_s"] for r in rows]), "active_s": _spread([r["active_s"] for r in rows]),
        "valid_change_call": _share(rows, "valid_change_call") if kind == "agent" else None,
        "trigger_seen": _share(rows, "trigger_seen", among="has_trigger") if kind != "local" else None,
    }


def directory_measures(directory: Path, data_root: Path) -> dict[str, Any]:
    """Secondary measures of one committed run directory (originals only). For development on dev outputs."""
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    m = summary["metadata"]
    if m.get("split", "dev") != "dev":
        raise ValueError(f"{directory.name}: m5_secondary's CLI reads dev outputs only (split {m.get('split')!r})")
    variant = m.get("variant")
    kind = "single_pass" if variant else "agent"
    rows = []
    for r in summary["runs"]:
        if r.get("variant", "original") != "original":
            continue
        sid = r["scenario_id"]
        events = read_trace(directory / "traces" / r["trace"])
        truth = GroundTruth.model_validate_json((data_root / "ground_truth" / f"{sid}.json").read_text(encoding="utf-8"))
        shown = agent_shown(events) if kind == "agent" else bundle_ids(data_root, sid, variant)
        rows.append(run_measures(kind, r, events, truth, load_observable(data_root / "scenarios" / sid), shown,
                                 (m.get("bounds") or {}).get("num_ctx")))
    return {"directory": directory.name, "kind": kind, "rows": rows, "aggregate": aggregate(kind, rows)}


def secondary_lines(arms: dict[str, dict[str, Any]]) -> list[str]:
    """Markdown tables for a {arm: aggregate} mapping."""
    def kn(x: dict[str, Any] | None) -> str:
        return "n/a" if x is None else f"{x['k']}/{x['n']}"

    def pct(x: dict[str, Any]) -> str:
        return f"{x['k']}/{x['n']}" + (f" ({x['pct']}%)" if x["pct"] is not None else "")

    def spread(x: dict[str, Any] | None, digits: int = 0) -> str:
        return "n/a" if x is None or x["median"] is None else f"{x['median']:.{digits}f} / {x['max']:.{digits}f}"

    lines = ["| Arm | Evidence headline | strict | lenient | Fabricated | Unsupported hyp. | Tool calls median / max "
             "| Wall s median / max | Active s median / max | Valid change-tool call | Trigger seen |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, a in arms.items():
        lines.append(f"| {name} | {pct(a['evidence_headline'])} | {pct(a['evidence_strict'])} | "
                     f"{pct(a['evidence_lenient'])} | {a['fabricated_citations']} | {kn(a['unsupported_hypotheses'])} | "
                     f"{spread(a['tool_calls'])} | {spread(a['wall_s'], 1)} | {spread(a['active_s'], 1)} | "
                     f"{kn(a['valid_change_call'])} | {kn(a['trigger_seen'])} |")
    agents = {name: a for name, a in arms.items() if a["investigated"]}
    if agents:
        lines += ["", "Investigated (a)-(f), runs meeting each (agent only; measures process, not insight):", "",
                  "| Arm | " + " | ".join(INVESTIGATED_PARTS) + " |", "|---|" + "---|" * len(INVESTIGATED_PARTS)]
        for name, a in agents.items():
            lines.append(f"| {name} | " + " | ".join(kn(a["investigated"][p]) for p in INVESTIGATED_PARTS) + " |")
    lines += ["", f"Budgets: the agent {AGENT_BUDGET} tool calls (3 loop-issued TRIAGE calls included); the rule "
              f"baseline {RULE_BASELINE_CALLS}. Single-pass makes no tool calls. Evidence validity pools the top-1 "
              "citations (correlated within a run; no interval). Hosted times include provider latency and are not "
              "evidence of quality."]
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sentinelops.evaluation.m5_secondary")
    parser.add_argument("--dir", type=Path, action="append", required=True, help="a dev run directory (repeatable)")
    parser.add_argument("--data-root", type=Path, default=Path("data/dev"))
    args = parser.parse_args(argv)
    try:
        results = {d.name: directory_measures(d, args.data_root)["aggregate"] for d in args.dir}
    except (ValueError, FileNotFoundError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print("\n".join(secondary_lines(results)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
