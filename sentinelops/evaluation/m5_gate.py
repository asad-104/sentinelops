"""M5 dev gate report: ``python -m sentinelops.evaluation.m5_gate --v1 DIR --v2 DIR``.

Pre-registered 2026-10-29 (docs/m5_preregistration.md, section 3 with amendments A1 and B5). A development check on
the 22 dev originals, not a result. v2 passes only if all of:
  G1  a change tool (list_deployments, list_config_changes, get_timeline) is called validly in at least 16 of the 22
      v2 runs; "validly" means the call returns at least one record and comes before the run's first
      submit_hypotheses
  G2  v2 valid reports >= v1 valid reports on the same 22
  G3  0 unknown_tool calls across the v2 runs
  G4  0 overflows in the v2 runs (trace overflow or context_exhausted)
Dev top-1 and the compaction-level distributions (all requests, HYPOTHESIZE, REPORT) are reported as information
only. Both arms must have exactly the 22 pre-registered runs, otherwise the gate is incomplete and does not pass.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any

from sentinelops.evaluation.agent_run import M5_DEV_SCENARIOS
from sentinelops.llm.trace import read_trace

CHANGE_TOOLS = frozenset({"list_deployments", "list_config_changes", "get_timeline"})
G1_MIN_RUNS = 16


def run_facts(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-run facts from one agent trace, in event order."""
    valid_change_call, before_ranking = False, True
    unknown = 0
    for e in events:
        if e["event"] != "tool" or e.get("by_loop"):
            continue
        if e["name"] == "submit_hypotheses":
            before_ranking = False
        if e.get("error_code") == "unknown_tool":
            unknown += 1
        if before_ranking and e["name"] in CHANGE_TOOLS and e.get("ok") and e.get("records"):
            valid_change_call = True
    contexts = [e for e in events if e["event"] == "context"]
    stop = next((e for e in events if e["event"] == "stop"), {})
    return {"valid_change_call": valid_change_call, "unknown_tool_calls": unknown,
            "levels": [c["level"] for c in contexts],
            "levels_hypothesize": [c["level"] for c in contexts if c["state"] == "HYPOTHESIZE"],
            "levels_report": [c["level"] for c in contexts if c["state"] == "REPORT"],
            "context_exhausted": stop.get("stop_reason") == "context_exhausted"}


def arm(directory: Path) -> dict[str, Any]:
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    rows = summary["runs"]
    facts = {r["scenario_id"]: run_facts(read_trace(directory / "traces" / r["trace"])) for r in rows}
    ids = [r["scenario_id"] for r in rows]

    def distribution(key: str) -> dict[int, int]:
        return dict(sorted(collections.Counter(level for f in facts.values() for level in f[key]).items()))

    return {"prompt_sha256": summary["metadata"]["prompt_sha256"], "prompt_version": summary["metadata"].get("prompt_version"),
            "complete": sorted(ids) == sorted(M5_DEV_SCENARIOS) and len(ids) == len(M5_DEV_SCENARIOS)
            and not summary["metadata"].get("aborted"),
            "runs": len(rows), "valid_reports": sum(r["report_valid"] for r in rows),
            "top1": sum(bool(r["top1"]) for r in rows),
            "valid_change_call_runs": sum(f["valid_change_call"] for f in facts.values()),
            "unknown_tool_calls": sum(f["unknown_tool_calls"] for f in facts.values()),
            "overflow_runs": sum((not r["investigated_f_no_overflow"]) or facts[r["scenario_id"]]["context_exhausted"]
                                 for r in rows),
            "levels_all": distribution("levels"), "levels_hypothesize": distribution("levels_hypothesize"),
            "levels_report": distribution("levels_report")}


def gate(v1_dir: Path, v2_dir: Path) -> dict[str, Any]:
    v1, v2 = arm(v1_dir), arm(v2_dir)
    complete = v1["complete"] and v2["complete"]
    checks = {"G1": v2["valid_change_call_runs"] >= G1_MIN_RUNS, "G2": v2["valid_reports"] >= v1["valid_reports"],
              "G3": v2["unknown_tool_calls"] == 0, "G4": v2["overflow_runs"] == 0}
    return {"complete": complete, "checks": checks, "passed": complete and all(checks.values()),
            "g1_threshold": f">= {G1_MIN_RUNS} of {len(M5_DEV_SCENARIOS)}", "v1": v1, "v2": v2,
            "note": "development check on the 22 dev scenarios, not a result; dev top-1 and levels are information only"}


def report_markdown(g: dict[str, Any]) -> str:
    v1, v2 = g["v1"], g["v2"]
    verdict = "PASSED" if g["passed"] else ("INCOMPLETE" if not g["complete"] else "FAILED")
    lines = ["# M5 dev gate (a development check, not a result)", "",
             f"v1 `{v1['prompt_sha256'][:12]}…`, v2 `{v2['prompt_sha256'][:12]}…`. **Gate: {verdict}**", "",
             "| Check | v1 | v2 | Requirement | Met |", "|---|---|---|---|---|",
             f"| G1 runs with a valid change-tool call before the first ranking | {v1['valid_change_call_runs']}/{v1['runs']} | "
             f"{v2['valid_change_call_runs']}/{v2['runs']} | v2 {g['g1_threshold']} | {g['checks']['G1']} |",
             f"| G2 valid reports | {v1['valid_reports']}/{v1['runs']} | {v2['valid_reports']}/{v2['runs']} | v2 >= v1 | "
             f"{g['checks']['G2']} |",
             f"| G3 unknown_tool calls | {v1['unknown_tool_calls']} | {v2['unknown_tool_calls']} | v2 = 0 | {g['checks']['G3']} |",
             f"| G4 overflow runs | {v1['overflow_runs']} | {v2['overflow_runs']} | v2 = 0 | {g['checks']['G4']} |", "",
             "Information only (not gated):", "",
             f"- dev top-1: v1 {v1['top1']}/{v1['runs']}, v2 {v2['top1']}/{v2['runs']}",
             f"- compaction levels, all requests: v1 {v1['levels_all']}, v2 {v2['levels_all']}",
             f"- at HYPOTHESIZE: v1 {v1['levels_hypothesize']}, v2 {v2['levels_hypothesize']}",
             f"- at REPORT: v1 {v1['levels_report']}, v2 {v2['levels_report']}", ""]
    if not g["complete"]:
        lines.insert(4, "**Incomplete:** both arms need exactly the 22 pre-registered runs and no abort.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sentinelops.evaluation.m5_gate")
    parser.add_argument("--v1", type=Path, required=True, help="the v1 dev-gate attempt directory")
    parser.add_argument("--v2", type=Path, required=True, help="the v2 dev-gate attempt directory")
    parser.add_argument("--out", type=Path, help="write the report JSON and Markdown here")
    args = parser.parse_args(argv)
    try:
        g = gate(args.v1, args.v2)
    except FileNotFoundError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    text = report_markdown(g)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "m5_dev_gate.json").write_text(json.dumps(g, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (args.out / "m5_dev_gate.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
