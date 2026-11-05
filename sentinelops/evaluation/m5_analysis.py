"""M5 headline analysis: ``python -m sentinelops.evaluation.m5_analysis``. No model call.

Pre-registered 2026-10-29 (docs/m5_preregistration.md section 7, A3) with deviation D1 (2026-11-05) and operational
changes O1-O2. Built before any fresh-split run.

- **Primary (D1):** top-1 on the 60 fresh originals, agent v1 against single-pass full: the discordant counts and an
  exact two-sided paired sign test on them, with its n. No pass/fail verdict.
- **Secondary:** top-1 and top-3 as k/n with Wilson 95% intervals for every arm (agent v1, single-pass full and
  no-timeline, the local baselines); valid reports; by tier (k/n with Wilson) and by fault type (counts only); the
  ablation (single-pass full against no-timeline, paired like the primary); natural exposure to the injected lines
  in the headline originals; the safety test's counts summed over its 3 slices (O1).

Directories: each arm has one directory per slice (``...-slice<K>``). A slice's ``-attempt2`` directory, if present,
replaces attempt 1; attempts are never merged, and any later attempt is refused. Every directory's metadata must
match the frozen fresh manifest, its slice's scenarios, the model and the arm's frozen hash, or the analysis refuses.
A missing or incomplete slice makes the analysis INCOMPLETE; the counts then cover the scenarios that ran.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sentinelops.agent.prompt import prompt_sha256
from sentinelops.agent.single_pass import SinglePassInvestigator, _ids, single_pass_sha256
from sentinelops.baselines import INVESTIGATORS
from sentinelops.evaluation import agent_run
from sentinelops.evaluation.agent_run import M5_AGENT_PROMPT, Refused
from sentinelops.evaluation.harness import DataMismatch, run_split, verify_split
from sentinelops.evaluation.metrics import wilson
from sentinelops.evaluation.safety import SAFETY_SLICES, plan, safety_slice
from sentinelops.llm.trace import read_trace
from sentinelops.scenario_files import dump_json
from sentinelops.simulator.datasets import DEFAULT_MANIFEST_DIR
from sentinelops.simulator.generator import GENERATOR_VERSION
from sentinelops.simulator.ground_truth import GroundTruth
from sentinelops.simulator.profiles import Split
from sentinelops.tools import ToolSet

AGENT, FULL, BARE = "agent_v1", "single_pass_full", "single_pass_no_timeline"
HOSTED_ARMS = (AGENT, FULL, BARE)
DEFAULT_MODEL, DEFAULT_BACKEND = "ministral-14b-2512", "mistral"
DEFAULT_OUT = Path("eval/m5") / f"generator-v{GENERATOR_VERSION}"
ATTEMPT = re.compile(r"-attempt(\d+)$")


def stems(backend: str, model: str) -> dict[str, str]:
    """The directory name of each hosted arm's slice K, without the attempt suffix (as the runners name them)."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", model)
    return {AGENT: f"m5-fresh-{backend}-{slug}-prompt-{M5_AGENT_PROMPT}-slice{{k}}",
            FULL: f"m5-fresh-single-pass-full-{backend}-{slug}-slice{{k}}",
            BARE: f"m5-fresh-single-pass-no-timeline-{backend}-{slug}-slice{{k}}",
            "safety": f"m5-safety-{backend}-{slug}-prompt-{M5_AGENT_PROMPT}-slice{{k}}"}


def resolve(root: Path, stem: str) -> tuple[Path | None, int | None]:
    """(directory, attempt) for one slice: attempt 2 if present, else attempt 1; None if neither exists."""
    later = sorted(int(m.group(1)) for p in root.glob(f"{stem}-attempt*")
                   if (m := ATTEMPT.search(p.name)) and p.name == f"{stem}-attempt{m.group(1)}")
    if any(a > 2 for a in later):
        raise Refused(f"{stem}: only one rerun per slice is allowed (attempt {max(later)} found)")
    if 2 in later:
        return root / f"{stem}-attempt2", 2
    return (root / stem, 1) if (root / stem).is_dir() else (None, None)


def sign_test(b: int, c: int) -> float:
    """Exact two-sided sign test on b and c discordant pairs (p = 0.5); 1.0 when there are none."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def paired(a: dict[str, dict[str, Any]], b: dict[str, dict[str, Any]], key: str = "top1") -> dict[str, Any]:
    """Discordant counts over the scenarios both arms ran: a right with b wrong, and the reverse."""
    both = sorted(set(a) & set(b))
    a_only = sum(a[s][key] and not b[s][key] for s in both)
    b_only = sum(b[s][key] and not a[s][key] for s in both)
    return {"n_pairs": len(both), "a_right_b_wrong": a_only, "b_right_a_wrong": b_only,
            "discordant": a_only + b_only, "p_two_sided": sign_test(a_only, b_only)}


def kn(k: int, n: int) -> dict[str, Any]:
    low, high = wilson(k, n)
    return {"k": k, "n": n, "wilson_95": [round(low, 4), round(high, 4)]}


def _expected_hash(arm: str) -> str:
    return prompt_sha256(M5_AGENT_PROMPT) if arm in (AGENT, "safety") else single_pass_sha256(
        "full" if arm == FULL else "no-timeline")


def load_arm(arm: str, root: Path, stem: str, slices: Sequence[Sequence[str]], model: str,
             manifest_sha256: str) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Per-scenario outcomes of one hosted arm over its slices, and one status row per slice."""
    outcomes: dict[str, dict[str, Any]] = {}
    status = []
    for k, ids in enumerate(slices, 1):
        directory, attempt = resolve(root, stem.format(k=k))
        if directory is None:
            status.append({"slice": k, "directory": None, "attempt": None, "complete": False, "runs": 0})
            continue
        summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
        m = summary["metadata"]
        hash_key = "prompt_sha256" if arm == AGENT else "single_pass_sha256"
        problems = [name for name, ok in (
            ("split", m.get("split") == Split.M5FRESH.value), ("slice", m.get("slice") == k),
            ("scenarios", list(m.get("scenarios", [])) == list(ids)), ("model", m.get("model") == model),
            ("manifest", m.get("manifest_sha256") == manifest_sha256), ("attempt", m.get("attempt") == attempt),
            ("hash", m.get(hash_key) == _expected_hash(arm)), ("twins", m.get("twins") is False)) if not ok]
        if problems:
            raise DataMismatch(f"{directory.name}: metadata does not match ({', '.join(problems)})")
        runs = [r for r in summary["runs"] if r.get("variant", "original") == "original"]
        complete = not m.get("aborted") and len(runs) == len(ids)
        for r in runs:
            outcomes[r["scenario_id"]] = {"top1": bool(r["top1"]), "top3": bool(r["top3"]),
                                          "valid": bool(r["report_valid"]), "trace": directory / "traces" / r["trace"]}
        status.append({"slice": k, "directory": directory.name, "attempt": attempt, "complete": complete,
                       "runs": len(runs), "git_commit": m.get("git_commit")})
    return outcomes, status


def local_arms(data_root: Path, manifest_dir: Path) -> dict[str, dict[str, dict[str, Any]]]:
    """The local baselines on the 60 fresh originals: deterministic, no model, no twins."""
    out = {}
    for name, investigator in INVESTIGATORS.items():
        result = run_split(investigator, Split.M5FRESH, data_root, manifest_dir=manifest_dir, twins=False)
        out[name] = {s.scenario_id: {"top1": s.top1, "top3": s.top3, "valid": s.report_valid} for s in result.scores}
    return out


def _injected_ids(truth: GroundTruth) -> set[str]:
    return set(truth.injection.source_ids) if truth.injection is not None else set()


def natural_exposure(agent: dict[str, dict[str, Any]], truths: dict[str, GroundTruth],
                     data_root: Path) -> dict[str, Any]:
    """Injected originals where injected lines reached the model without the forced call. Agent: an injected ID
    among the IDs a tool call showed it (from the trace). Single-pass: an injected ID in the rendered bundle
    (rebuilt from the data with the frozen rule; independent of the model)."""
    injected = sorted(s for s, t in truths.items() if t.injection is not None)
    agent_ran = [s for s in injected if s in agent]
    agent_shown = sum(bool(_injected_ids(truths[s]) & {i for e in read_trace(agent[s]["trace"])
                                                      if e["event"] == "tool" for i in e.get("new_ids") or []})
                      for s in agent_ran)
    bundles = {}
    for variant in ("full", "no-timeline"):
        hit = 0
        for s in injected:
            messages, _, _ = SinglePassInvestigator(None, variant=variant)._fitting_request(
                ToolSet.from_directory(data_root / "scenarios", s))
            text = "\n".join(m.content for m in (messages or [])[1:])
            hit += bool(_injected_ids(truths[s]) & _ids(text))
        bundles[variant] = hit
    return {"injected_originals": len(injected), "agent_runs": len(agent_ran), "agent_exposed": agent_shown,
            "single_pass_full_exposed": bundles["full"], "single_pass_no_timeline_exposed": bundles["no-timeline"],
            "note": "agent from traces; single-pass from the rebuilt bundle"}


def load_safety(root: Path, stem: str, data_root: Path, manifest_dir: Path, model: str,
                manifest_sha256: str) -> dict[str, Any]:
    exposed = [p.scenario_id for p in plan(Split.M5FRESH, data_root, manifest_dir) if p.window_min is not None]
    totals: dict[str, int] = {}
    status = []
    for k in range(1, SAFETY_SLICES + 1):
        directory, attempt = resolve(root, stem.format(k=k))
        if directory is None:
            status.append({"slice": k, "directory": None, "attempt": None, "complete": False})
            continue
        summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
        m = summary["metadata"]
        if (m.get("slice"), list(m.get("scenarios", [])), m.get("model"), m.get("manifest_sha256"), m.get("attempt"),
                m.get("prompt_sha256")) != (k, safety_slice(exposed, k), model, manifest_sha256, attempt,
                                            _expected_hash("safety")):
            raise DataMismatch(f"{directory.name}: metadata does not match its safety slice")
        for key, value in summary["counts"].items():
            if key != "complete":
                totals[key] = totals.get(key, 0) + int(value)
        status.append({"slice": k, "directory": directory.name, "attempt": attempt,
                       "complete": bool(summary["counts"]["complete"])})
    return {"exposed_pairs": len(exposed), "counts": totals, "slices": status,
            "complete": all(s["complete"] for s in status)}


def analyse(agent_root: Path, safety_root: Path, data_root: Path, manifest_dir: Path = DEFAULT_MANIFEST_DIR,
            backend: str = DEFAULT_BACKEND, model: str = DEFAULT_MODEL, local: bool = True) -> dict[str, Any]:
    manifest = verify_split(Split.M5FRESH, data_root, manifest_dir)
    slices = [agent_run.fresh_slice(manifest_dir, k) for k in range(1, agent_run.FRESH_SLICES + 1)]
    names = stems(backend, model)
    arms: dict[str, dict[str, dict[str, Any]]] = {}
    status = {}
    for arm in HOSTED_ARMS:
        arms[arm], status[arm] = load_arm(arm, agent_root, names[arm], slices, model, manifest["content_sha256"])
    if local:
        arms.update(local_arms(data_root, manifest_dir))
    truths = {s: GroundTruth.model_validate_json((data_root / "ground_truth" / f"{s}.json").read_text(encoding="utf-8"))
              for s in manifest["scenario_ids"]}
    tiers = sorted({t.tier.value for t in truths.values()})
    faults = sorted({t.diagnosis.fault_type.value for t in truths.values()})

    def per_arm(outcomes: dict[str, dict[str, Any]]) -> dict[str, Any]:
        n = len(outcomes)
        row = {"top1": kn(sum(o["top1"] for o in outcomes.values()), n),
               "top3": kn(sum(o["top3"] for o in outcomes.values()), n),
               "valid_reports": {"k": sum(o["valid"] for o in outcomes.values()), "n": n},
               "by_tier": {}, "by_fault_type": {}}
        for tier in tiers:
            ids = [s for s in outcomes if truths[s].tier.value == tier]
            row["by_tier"][tier] = {"top1": kn(sum(outcomes[s]["top1"] for s in ids), len(ids)),
                                    "top3": kn(sum(outcomes[s]["top3"] for s in ids), len(ids))}
        for fault in faults:  # counts only, no intervals or rates (section 7)
            ids = [s for s in outcomes if truths[s].diagnosis.fault_type.value == fault]
            row["by_fault_type"][fault] = {"top1": sum(outcomes[s]["top1"] for s in ids),
                                           "top3": sum(outcomes[s]["top3"] for s in ids), "n": len(ids)}
        return row

    complete = all(s["complete"] for rows in status.values() for s in rows)
    safety = load_safety(safety_root, names["safety"], data_root, manifest_dir, model, manifest["content_sha256"])
    commits = sorted({s.get("git_commit") for rows in status.values() for s in rows if s.get("git_commit")})
    return {
        "metadata": {"split": Split.M5FRESH.value, "manifest_sha256": manifest["content_sha256"],
                     "n_scenarios": len(manifest["scenario_ids"]), "backend": backend, "model": model,
                     "agent_prompt_sha256": prompt_sha256(M5_AGENT_PROMPT), "run_commits": commits,
                     "complete": complete, "safety_complete": safety["complete"],
                     "note": "D1 primary; no pass/fail verdict; synthetic, author-built data; co-adaptation caveat (A5)"},
        "slices": status,
        "primary": {"metric": "top-1, agent v1 against single-pass full, exact two-sided paired sign test",
                    **paired(arms[AGENT], arms[FULL])},
        "ablation": {"metric": "top-1, single-pass full against no-timeline (secondary)", **paired(arms[FULL], arms[BARE])},
        "arms": {name: per_arm(outcomes) for name, outcomes in arms.items()},
        "natural_exposure": natural_exposure(arms[AGENT], truths, data_root),
        "safety": safety,
    }


def _ci(x: dict[str, Any]) -> str:
    return f"{x['k']}/{x['n']} [{x['wilson_95'][0]:.2f}, {x['wilson_95'][1]:.2f}]"


def report_markdown(a: dict[str, Any]) -> str:
    m, p, ab = a["metadata"], a["primary"], a["ablation"]
    lines = ["# M5 headline analysis (fresh split)", "",
             f"Manifest `{m['manifest_sha256'][:12]}…`, model `{m['model']}`, agent prompt `{m['agent_prompt_sha256'][:12]}…`, "
             f"run commits {', '.join(m['run_commits']) or '–'}. Synthetic, author-built data; the simulator, the "
             "baselines and the prompts share an author (A5). Counts with intervals, not rates. No pass/fail verdict.", ""]
    if not m["complete"]:
        missing = [f"{arm} slice {s['slice']}" for arm, rows in a["slices"].items() for s in rows if not s["complete"]]
        lines += [f"**INCOMPLETE:** {', '.join(missing)}. Counts cover the scenarios that ran.", ""]
    lines += ["## Primary (D1)", "",
              f"Top-1, agent v1 against single-pass full, over {p['n_pairs']} paired originals: agent right and "
              f"single-pass wrong **{p['a_right_b_wrong']}**, the reverse **{p['b_right_a_wrong']}**; exact two-sided "
              f"sign test on n = {p['discordant']} discordant pairs, p = {p['p_two_sided']:.4f}.", "",
              "## Every arm (secondary)", "", "| Arm | Top-1 [Wilson 95%] | Top-3 [Wilson 95%] | Valid reports |",
              "|---|---|---|---|"]
    for name, r in a["arms"].items():
        lines.append(f"| {name} | {_ci(r['top1'])} | {_ci(r['top3'])} | {r['valid_reports']['k']}/{r['valid_reports']['n']} |")
    tiers = list(next(iter(a["arms"].values()))["by_tier"])
    lines += ["", "## By tier (top-1, k/n with Wilson 95%)", "", "| Arm | " + " | ".join(tiers) + " |",
              "|---|" + "---|" * len(tiers)]
    for name, r in a["arms"].items():
        lines.append(f"| {name} | " + " | ".join(_ci(r["by_tier"][t]["top1"]) for t in tiers) + " |")
    faults = list(next(iter(a["arms"].values()))["by_fault_type"])
    lines += ["", "## By fault type (top-1 / top-3 / n, counts only)", "", "| Arm | " + " | ".join(faults) + " |",
              "|---|" + "---|" * len(faults)]
    for name, r in a["arms"].items():
        lines.append(f"| {name} | " + " | ".join(
            f"{r['by_fault_type'][f]['top1']} / {r['by_fault_type'][f]['top3']} / {r['by_fault_type'][f]['n']}"
            for f in faults) + " |")
    ne, s = a["natural_exposure"], a["safety"]
    lines += ["", "## Ablation (secondary)", "",
              f"Top-1, single-pass full against no-timeline over {ab['n_pairs']} paired originals: full right and "
              f"no-timeline wrong {ab['a_right_b_wrong']}, the reverse {ab['b_right_a_wrong']}; sign test n = "
              f"{ab['discordant']}, p = {ab['p_two_sided']:.4f}.", "",
              "## Natural exposure in the headline originals (secondary)", "",
              f"Of {ne['injected_originals']} injected originals: agent shown an injected line in {ne['agent_exposed']} "
              f"of {ne['agent_runs']} runs; single-pass bundle contains one in {ne['single_pass_full_exposed']} (full) and "
              f"{ne['single_pass_no_timeline_exposed']} (no-timeline). {ne['note']}.", "",
              "## Safety test (separate, labelled; summed over its slices)", "",
              f"Exposed pairs {s['exposed_pairs']}; " + (", ".join(f"{k} {v}" for k, v in s["counts"].items()) or "no slice run")
              + ("" if s["complete"] else " (INCOMPLETE)"), ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sentinelops.evaluation.m5_analysis")
    parser.add_argument("--agent-root", type=Path, default=Path("eval/agent") / f"generator-v{GENERATOR_VERSION}")
    parser.add_argument("--safety-root", type=Path, default=Path("eval/safety") / f"generator-v{GENERATOR_VERSION}")
    parser.add_argument("--data-root", type=Path, default=Path("data") / Split.M5FRESH.value)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    try:
        result = analyse(args.agent_root, args.safety_root, args.data_root, args.manifest_dir, model=args.model)
    except (Refused, DataMismatch, FileNotFoundError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    text = report_markdown(result)
    args.out.mkdir(parents=True, exist_ok=True)
    dump_json(args.out / "m5_analysis.json", json.loads(json.dumps(result, default=str)))
    (args.out / "m5_analysis.md").write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
