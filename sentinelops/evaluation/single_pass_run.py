"""M5 single-pass baseline runs, dev only for now: ``python -m sentinelops.evaluation.single_pass_run``.

``--variant full|no-timeline`` (pre-registered 2026-10-29). ``--set dev-gate`` runs the 22 pre-registered dev
originals (the mechanics check; accuracy is information only). Originals only, never twins. Reuses the agent
runner's hosted data guard, provider settings, run guard, attempt directories and refusal to overwrite. The fresh
split is added with its generator (stage D).
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from sentinelops.agent.single_pass import VARIANTS, SinglePassInvestigator, single_pass_sha256
from sentinelops.evaluation.agent_run import (
    DEFAULT_OUT_ROOT,
    HOSTED_BACKENDS,
    M5_DEV_SCENARIOS,
    Refused,
    check_hosted_target,
)
from sentinelops.evaluation.harness import DataMismatch, HarnessAbort, git_commit, run_split, verify_split
from sentinelops.evaluation.pilot import MAX_SWAP_GROWTH_GB, MIN_FREE_GB, GuardedInvestigator, OutputExists, system_stats
from sentinelops.llm.client import LLMClient
from sentinelops.llm.openai_compat import DisallowedEndpoint, MissingKey, OpenAICompatibleClient, RateLimits
from sentinelops.llm.trace import TraceWriter, read_trace
from sentinelops.scenario_files import dump_json
from sentinelops.simulator.datasets import DEFAULT_MANIFEST_DIR
from sentinelops.simulator.generator import GENERATOR_VERSION
from sentinelops.simulator.ground_truth import GroundTruth
from sentinelops.simulator.profiles import Split


def rows(trace_dir: Path, data_root: Path) -> list[dict[str, Any]]:
    out = []
    for path in sorted(trace_dir.glob("*.jsonl")):
        events = read_trace(path)
        start = next(e for e in events if e["event"] == "start")
        stop = next((e for e in events if e["event"] == "stop"), None)
        bundle = next((e for e in events if e["event"] == "bundle"), {})
        truth = GroundTruth.model_validate_json((data_root / "ground_truth" / f"{start['scenario_id']}.json")
                                                .read_text(encoding="utf-8"))
        report = stop["report"] if stop else None
        pairs = [(h["service"], h["fault_type"]) for h in (report or {}).get("hypotheses", [])]
        answer = (truth.diagnosis.service.value, truth.diagnosis.fault_type.value)
        models = [e for e in events if e["event"] == "model"]
        out.append({"run": len(out) + 1, "trace": path.name, "scenario_id": start["scenario_id"],
                    "tier": truth.tier.value, "stop_reason": stop["stop_reason"] if stop else "error",
                    "report_valid": report is not None, "top1": bool(pairs) and pairs[0] == answer,
                    "top3": answer in pairs[:3], "top": list(pairs[0]) if pairs else None,
                    "requests": len(models), "estimated_tokens": bundle.get("estimated_tokens"),
                    "reductions": bundle.get("reductions"),
                    "prompt_tokens": sum(e.get("prompt_tokens") or 0 for e in models),
                    "completion_tokens": sum(e.get("completion_tokens") or 0 for e in models),
                    "wait_s": round(sum(e.get("wait_s") or 0.0 for e in models), 3),
                    "elapsed_s": stop["elapsed_s"] if stop else None})
    return out


def run_single_pass(client: LLMClient, backend: str, model: str, variant: str, data_root: Path, out_dir: Path,
                    scenario_ids: Sequence[str], manifest_dir: Path = DEFAULT_MANIFEST_DIR,
                    min_free_gb: float = MIN_FREE_GB, stats: Any = None,
                    clock: Callable[[], float] = time.monotonic, attempt: int = 1) -> dict[str, Any]:
    if backend in HOSTED_BACKENDS:
        check_hosted_target(data_root, scenario_ids, manifest_dir)
    trace_dir = out_dir / "traces"
    if any(trace_dir.glob("*.jsonl")) or (out_dir / "run_log.jsonl").exists():
        raise OutputExists(f"{out_dir} already holds an attempt; use a new --attempt number")
    manifest = verify_split(Split.DEV, data_root, manifest_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    unload = getattr(client, "unload", None)
    inner = SinglePassInvestigator(client, variant=variant, traces=TraceWriter(trace_dir), clock=clock)
    guarded = GuardedInvestigator(inner, out_dir / "run_log.jsonl", out_dir, min_free_gb=min_free_gb,
                                  max_swap_growth_gb=MAX_SWAP_GROWTH_GB, stats=stats or system_stats, after_run=unload)
    aborted: HarnessAbort | None = None
    try:
        run_split(guarded, Split.DEV, data_root, manifest_dir=manifest_dir, scenario_ids=scenario_ids, twins=False)
    except HarnessAbort as exc:
        aborted = exc
    runs = rows(trace_dir, data_root)
    summary = {"metadata": {"backend": backend, "model": model, "client": client.describe(), "variant": variant,
                            "single_pass_sha256": single_pass_sha256(variant), "scenarios": list(scenario_ids),
                            "generator_version": manifest["generator_version"],
                            "manifest_sha256": manifest["content_sha256"], "git_commit": git_commit(),
                            "attempt": attempt, "aborted": None if aborted is None else str(aborted), "twins": False},
               "runs": runs,
               "counts": {"n": len(runs), "valid_reports": sum(r["report_valid"] for r in runs),
                          "top1": sum(r["top1"] for r in runs), "top3": sum(r["top3"] for r in runs),
                          "complete": aborted is None and len(runs) == len(scenario_ids)}}
    dump_json(out_dir / "summary.json", summary)
    (out_dir / "summary.md").write_text(summary_markdown(summary), encoding="utf-8", newline="\n")
    if aborted is not None:
        raise aborted
    return summary


def summary_markdown(summary: dict[str, Any]) -> str:
    m, c = summary["metadata"], summary["counts"]
    lines = [f"# M5 single-pass baseline ({m['variant']}): {m['backend']} ({m['model']}), attempt {m['attempt']}", "",
             f"Hash `{m['single_pass_sha256'][:12]}…`, code `{m['git_commit']}`. One request per scenario, a fixed "
             "evidence bundle, frozen before the first call and never tuned. Counts, not rates.", "",
             "| Run | Scenario | Tier | Stop | Valid report | Top-1 | Top-3 | Requests | Est tokens | Reductions |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in summary["runs"]:
        lines.append(f"| {r['run']} | {r['scenario_id']} | {r['tier']} | {r['stop_reason']} | "
                     f"{'yes' if r['report_valid'] else 'no'} | {r['top1']} | {r['top3']} | {r['requests']} | "
                     f"{r['estimated_tokens']} | {', '.join(r['reductions'] or []) or '–'} |")
    lines += ["", f"valid reports {c['valid_reports']}/{c['n']}, top-1 {c['top1']}/{c['n']}, top-3 {c['top3']}/{c['n']}"
              f"{'' if c['complete'] else ' (INCOMPLETE)'}", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sentinelops.evaluation.single_pass_run")
    parser.add_argument("--backend", choices=("mistral",), required=True)
    parser.add_argument("--model", required=True, help="the pinned dated model ID")
    parser.add_argument("--rpm", type=int, required=True)
    parser.add_argument("--tpm", type=int, required=True)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--set", choices=("dev-gate",), required=True)
    parser.add_argument("--data-root", type=Path, default=Path("data/dev"))
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args(argv)
    try:
        client = OpenAICompatibleClient(args.backend, args.model, limits=RateLimits(args.rpm, args.tpm),
                                        max_tokens=2048)
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", args.model)
        name = (f"m5-dev-gate-single-pass-{args.variant}-{args.backend}-{slug}"
                f"{f'-attempt{args.attempt}' if args.attempt > 1 else ''}")
        out_dir = args.out_root / f"generator-v{GENERATOR_VERSION}" / name
        summary = run_single_pass(client, args.backend, args.model, args.variant, args.data_root, out_dir,
                                  M5_DEV_SCENARIOS, args.manifest_dir, attempt=args.attempt)
    except (Refused, DataMismatch, HarnessAbort, OutputExists, FileNotFoundError, MissingKey, DisallowedEndpoint) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(summary_markdown(summary))
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
