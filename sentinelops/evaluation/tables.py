"""Markdown tables: counts with percentages and Wilson 95% intervals, floors beside the baseline."""

from __future__ import annotations

from typing import Any

from sentinelops.evaluation.metrics import N_PAIRS, RANDOM_FLOOR
from sentinelops.simulator.profiles import Tier


def _cell(rate: dict[str, Any]) -> str:
    if not rate["n"]:
        return "n/a"
    lo, hi = rate["ci95"]
    return f"{rate['k']}/{rate['n']} ({rate['pct']:.0f}%, {lo:.0f}–{hi:.0f})"


def _pct(block: dict[str, Any]) -> str:
    return "n/a" if block["pct"] is None else f"{block['k']}/{block['n']} ({block['pct']:.0f}%)"


def _random_row(n_label: str) -> str:
    r = RANDOM_FLOOR
    return (f"| random (analytical, 1/{N_PAIRS} pairs) | {n_label} | {100 * r['top1']:.1f}% | {100 * r['top3']:.1f}% "
            f"| {100 * r['service_top1']:.0f}% | – | – | – |")


def accuracy_table(summaries: dict[str, dict[str, Any]], key: str = "overall", tier: str | None = None) -> str:
    lines = ["| Investigator | n | Top-1 | Top-3 | Service top-1 | Evidence (headline: strict, excl. alert) "
             "| Evidence (strict incl. alert, M2b) | Evidence (lenient, M2b) |",
             "|---|---|---|---|---|---|---|---|"]
    n_label = ""
    for name, summary in summaries.items():
        block = summary["overall"] if tier is None else summary["per_tier"][tier]
        n_label = str(block["n"])
        lines.append(f"| {name} | {block['n']} | {_cell(block['top1'])} | {_cell(block['top3'])} "
                     f"| {_cell(block['service_top1'])} | {_pct(block['evidence_headline'])} "
                     f"| {_pct(block['evidence_strict'])} | {_pct(block['evidence_lenient'])} |")
    lines.append(_random_row(n_label))
    return "\n".join(lines)


def operations_table(summaries: dict[str, dict[str, Any]]) -> str:
    lines = ["| Investigator | Missing evidence named (missing tier) | Unsupported hypotheses | Fabricated citations "
             "| Injection cited | Injection followed | Tool calls (mean / max) | Latency ms (median / p95) | Cost (USD) |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, summary in summaries.items():
        b = summary["overall"]
        lines.append(f"| {name} | {_cell(b['missing_evidence_named'])} | {b['unsupported_hypotheses']['k']}/{b['unsupported_hypotheses']['n']} "
                     f"| {b['fabricated_citations']} | {_cell(b['injection_cited'])} | {_cell(b['injection_followed'])} "
                     f"| {b['tool_calls_mean']:.1f} / {b['tool_calls_max']} "
                     f"| {b['latency_ms_median']:.1f} / {b['latency_ms_p95']:.1f} | {b['cost_usd_total']:.2f} |")
    return "\n".join(lines)


def per_fault_table(summaries: dict[str, dict[str, Any]]) -> str:
    faults = list(next(iter(summaries.values()))["per_fault_descriptive"])
    lines = ["| Investigator | " + " | ".join(faults) + " |", "|---|" + "---|" * len(faults)]
    for name, summary in summaries.items():
        cells = [f"{summary['per_fault_descriptive'][f]['top1']}/{summary['per_fault_descriptive'][f]['n']}"
                 for f in faults]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def full_report(summaries: dict[str, dict[str, Any]], split: str, metadata: dict[str, Any]) -> str:
    parts = [
        f"# {split} results",
        "",
        f"Generator version {metadata['generator_version']}, data sha256 `{metadata['manifest_sha256'][:12]}…`, "
        f"code `{metadata['git_commit']}`, call budget {metadata['call_budget']}. "
        "Cells are k/n (%, Wilson 95% interval). Evidence validity is pooled over top-1 citations and has no "
        "interval because citations within a scenario are correlated. The headline definition counts only fault "
        "logs and the trigger change; the two M2b definitions are kept for comparison.",
        "",
        "## Overall",
        accuracy_table(summaries),
    ]
    for tier in Tier:
        parts += ["", f"## Tier: {tier.value}", accuracy_table(summaries, tier=tier.value)]
    parts += ["", "## Claims, injection and cost (overall)", operations_table(summaries),
              "", "## Top-1 by fault type (descriptive counts only; cells are too small for claims)",
              per_fault_table(summaries), ""]
    return "\n".join(parts)
