"""Paired tier ablation, dev only: ``python -m sentinelops.evaluation.ablation``.

For every dev scenario where a mechanism (injection, overlap, decoy, gap) is on, its twin with only
that mechanism switched off is generated in memory. Independent random streams make the twin the
same scenario otherwise (tests/test_streams.py). Each investigator runs on both, and outcomes are
counted as pairs. The "on" side is checked to equal the frozen dev data on disk. There is no split
argument: the held-out split cannot be ablated.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from sentinelops.baselines import INVESTIGATORS
from sentinelops.evaluation.harness import (
    DEFAULT_CALL_BUDGET,
    CountingToolSet,
    DataMismatch,
    git_commit,
    verify_split,
)
from sentinelops.report import InvestigationReport, Investigator
from sentinelops.scenario_files import dump_json, load_observable
from sentinelops.simulator.datasets import DEFAULT_MANIFEST_DIR, SPLIT_SEEDS, split_schedule
from sentinelops.simulator.generator import GENERATOR_VERSION, Scenario, generate_scenario
from sentinelops.simulator.profiles import MECHANISM_NAMES, PROFILES, Mechanisms, Split
from sentinelops.tools import ToolSet

DEFAULT_RESULTS_ROOT = Path("eval/results")


def _top(report: InvestigationReport) -> tuple[str, str]:
    return (report.top.service.value, report.top.fault_type.value)


def _run(investigator: Investigator, scenario: Scenario, budget: int) -> InvestigationReport:
    tools = CountingToolSet(ToolSet(scenario.observable), budget)
    return investigator.investigate(tools, scenario.observable.scenario_id)


def paired_counts(pairs: list[tuple[tuple[str, str], tuple[str, str], tuple[str, str]]]) -> dict[str, int]:
    """Counts over (truth, top-1 with mechanism on, top-1 with it off) triples."""
    return {
        "n": len(pairs),
        "unchanged": sum(on == off for _, on, off in pairs),
        "both_correct": sum(on == truth == off for truth, on, off in pairs),
        "both_wrong": sum(on != truth and off != truth for truth, on, off in pairs),
        "correct_only_without": sum(off == truth != on for truth, on, off in pairs),
        "correct_only_with": sum(on == truth != off for truth, on, off in pairs),
    }


def twin_cases(mechanism: str, data_root: Path) -> list[tuple[Scenario, Scenario]]:
    """(original, twin with ``mechanism`` off) for every dev scenario where it is on."""
    split = Split.DEV
    profile, seed = PROFILES[split], SPLIT_SEEDS[split]
    cases = []
    for i, (fault, tier) in enumerate(split_schedule(split)):
        mechanisms = Mechanisms.for_tier(tier)
        if not getattr(mechanisms, mechanism):
            continue
        original = generate_scenario(seed, i, fault, tier, profile)
        if mechanism == "injection" and original.ground_truth.injection is None:
            continue
        scenario_id = original.observable.scenario_id
        if load_observable(data_root / "scenarios" / scenario_id) != original.observable:
            raise RuntimeError(f"regenerated {scenario_id} differs from the frozen dev data")
        twin = generate_scenario(seed, i, fault, tier, profile, replace(mechanisms, **{mechanism: False}))
        cases.append((original, twin))
    return cases


def run_ablation(investigators: dict[str, Investigator], data_root: Path,
                 manifest_dir: Path = DEFAULT_MANIFEST_DIR, budget: int = DEFAULT_CALL_BUDGET) -> dict[str, Any]:
    manifest = verify_split(Split.DEV, data_root, manifest_dir)
    results: dict[str, dict[str, dict[str, int]]] = {}
    for mechanism in MECHANISM_NAMES:
        cases = twin_cases(mechanism, data_root)
        results[mechanism] = {}
        for name, investigator in investigators.items():
            triples = []
            for original, twin in cases:
                truth = original.ground_truth.diagnosis
                triples.append(((truth.service.value, truth.fault_type.value),
                                _top(_run(investigator, original, budget)), _top(_run(investigator, twin, budget))))
            results[mechanism][name] = paired_counts(triples)
    return {"split": "dev", "metadata": {"generator_version": manifest["generator_version"],
                                         "manifest_sha256": manifest["content_sha256"],
                                         "git_commit": git_commit(), "call_budget": budget},
            "ablation": results}


def ablation_table(result: dict[str, Any]) -> str:
    meta = result["metadata"]
    lines = [
        "# dev paired ablation",
        "",
        f"Generator version {meta['generator_version']}, data sha256 `{meta['manifest_sha256'][:12]}…`, code "
        f"`{meta['git_commit']}`. Each row pairs the dev scenarios where the mechanism is on with the same "
        "scenarios with only that mechanism switched off. Counts, not rates: cells are small. Injection: "
        "scenarios with injected lines (any tier). Overlap and decoy: ambiguous tier. Gap: missing-evidence tier.",
        "",
        "| Mechanism | Investigator | n | Unchanged top-1 | Both correct | Both wrong "
        "| Correct only without it | Correct only with it |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for mechanism, per_investigator in result["ablation"].items():
        for name, c in per_investigator.items():
            lines.append(f"| {mechanism} | {name} | {c['n']} | {c['unchanged']}/{c['n']} | {c['both_correct']} "
                         f"| {c['both_wrong']} | {c['correct_only_without']} | {c['correct_only_with']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sentinelops.evaluation.ablation",
                                     description="Paired tier ablation on the dev split.")
    parser.add_argument("--data-root", type=Path, default=Path("data/dev"))
    parser.add_argument("--out-dir", type=Path, help="default: eval/results/generator-v<version>")
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        result = run_ablation(INVESTIGATORS, args.data_root, args.manifest_dir)
    except DataMismatch as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    out_dir = args.out_dir or DEFAULT_RESULTS_ROOT / f"generator-v{GENERATOR_VERSION}"
    out_dir.mkdir(parents=True, exist_ok=True)
    dump_json(out_dir / "dev-ablation.json", result)
    table = ablation_table(result)
    (out_dir / "dev-ablation.md").write_text(table, encoding="utf-8", newline="\n")
    print(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
