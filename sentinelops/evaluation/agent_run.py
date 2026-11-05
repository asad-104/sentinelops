"""M4 agent runs, dev only: ``python -m sentinelops.evaluation.agent_run --backend mock|ollama|groq|mistral``.

- ``--backend groq`` (hosted free tier, decision 2026-10-28) behaves like ``ollama``: the key comes only from
  ``GROQ_API_KEY``; provider rate-limit waits are recorded per turn and summed per run.
- ``--backend mistral`` (pre-registered 2026-10-29) is the same, with the key from ``MISTRAL_API_KEY``. The
  pinned ``--model`` and the console's ``--rpm``/``--tpm`` are required. Hosted backends receive only the
  verified dev split: no held-out root and no scenario outside the dev manifest (``check_hosted_target``).
- ``--backend ollama`` (stage B only) runs the fixed 10 core scenarios (pre-registered 2026-10-23); the
  harness also runs the injection twins. ``--smoke ID`` runs one scenario outside the core set instead.
- ``--backend mock`` runs every scenario in the manifest it is given, which must be a set generated in a
  temporary directory: it refuses any core scenario and any output under ``eval/agent/`` (no tuning on
  the core set; stage A mock traces never touch the real results directory).
Reuses the pilot's guard (free disk, swap growth, memory pressure), unload after every run, attempt
directories, refusal to overwrite and summary on abort.

``--split m5fresh --slice K`` (M5 headline, pre-registered 2026-10-29 section 5 and A2): one of the 6 fixed slices
of 10 fresh originals, cut from the frozen m5fresh manifest's order. Mistral only, prompt v1 only (v2 failed the dev
gate, 2026-11-02), originals only. The M4 decision rule is not applied as an M5 verdict (section 7).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sentinelops.agent.machine import StateMachineInvestigator
from sentinelops.agent.mock import DemoAgentPolicy
from sentinelops.agent.prompt import prompt_sha256
from sentinelops.agent.states import AgentBounds
from sentinelops.evaluation.agent_metrics import investigated, shallow_measures
from sentinelops.evaluation.harness import DataMismatch, HarnessAbort, git_commit, run_split, verify_split
from sentinelops.evaluation.pilot import (
    MAX_SWAP_GROWTH_GB,
    MIN_FREE_GB,
    PILOT_SCENARIOS,
    GuardedInvestigator,
    OutputExists,
    Progress,
    ProgressClient,
    system_stats,
)
from sentinelops.llm.client import LLMClient
from sentinelops.llm.ollama import OllamaClient
from sentinelops.llm.openai_compat import DisallowedEndpoint, MissingKey, OpenAICompatibleClient, RateLimits
from sentinelops.llm.trace import TraceWriter, read_trace
from sentinelops.scenario_files import dump_json, load_observable
from sentinelops.simulator.datasets import DEFAULT_MANIFEST_DIR, TWINS_DIR
from sentinelops.simulator.generator import GENERATOR_VERSION
from sentinelops.simulator.ground_truth import GroundTruth
from sentinelops.simulator.profiles import Split

# Fixed 2026-10-23: first 2 per fault type in dev manifest order, excluding the M3 pilot and smoke scenarios.
CORE_SCENARIOS = ("sc-30385ffc64", "sc-3836c69ef7", "sc-3e3ceb314e", "sc-4001bf784c", "sc-408b514aeb",
                  "sc-4251e8920a", "sc-497fd61898", "sc-5b55b772de", "sc-5c5b9b9197", "sc-91404ea5fc")
M3_SMOKE_SCENARIO = "sc-2c422896a9"
M4_SMOKE_SCENARIO = "sc-45fa1390ea"
# M5 dev gate (pre-registered 2026-10-29, docs/m5_preregistration.md section 2): the 22 dev scenarios never used before.
M5_DEV_SCENARIOS = ("sc-47610c9e02", "sc-694130798c", "sc-6d023322e9", "sc-8e6dbe7f20", "sc-918356ee90", "sc-9969d4b81d",
                    "sc-a59e0e61c7", "sc-ba353abbc7", "sc-be7c6ab28b", "sc-be91d5105d", "sc-bf8ef04f56", "sc-c1e7d959c8",
                    "sc-cc007aa1ee", "sc-d74c46a899", "sc-dca259caa6", "sc-df583a5a54", "sc-e2cea1c0c0", "sc-ec3e7c879f",
                    "sc-f7e6249083", "sc-fada5df47f", "sc-fb1c777397", "sc-ff655f01df")
# M5 headline slices (pre-registered 2026-10-29 section 5): the frozen m5fresh manifest's order, cut into 6 slices of 10.
FRESH_SLICES, FRESH_SLICE_SIZE = 6, 10
# The dev gate failed (2026-11-02, report 52daa08): every M5 fresh-split agent run uses v1 (d269d28d).
M5_AGENT_PROMPT = "v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_RESULTS = REPO_ROOT / "eval" / "agent"
DEFAULT_OUT_ROOT = Path("eval/agent")


HOSTED_BACKENDS = frozenset({"groq", "mistral"})


class Refused(Exception):
    """A run the pre-registration forbids (core scenarios with the mock, mock output in eval/agent/, or
    anything but synthetic dev data sent to a hosted backend)."""


def check_mock_target(scenario_ids: Sequence[str], out_dir: Path) -> None:
    core = sorted(set(scenario_ids) & set(CORE_SCENARIOS))
    if core:
        raise Refused(f"the mock backend must not run core scenarios ({len(core)} found); use a generated set")
    if out_dir.resolve().is_relative_to(REAL_RESULTS):
        raise Refused("mock traces must not be written under eval/agent/; use a temporary directory")


def manifest_ids(split: Split, manifest_dir: Path) -> set[str]:
    """The scenario IDs a frozen manifest lists (the data guard's membership set). Never printed."""
    return set(json.loads((manifest_dir / f"{split.value}.json").read_text(encoding="utf-8"))["scenario_ids"])


def check_hosted_target(data_root: Path, scenario_ids: Sequence[str], manifest_dir: Path,
                        split: Split = Split.DEV) -> None:
    """Data rule (2026-10-29): only synthetic dev data, and the M5 fresh split (pre-registered allowance), goes to a
    hosted provider; held-out never does. The split itself is then verified against its frozen manifest."""
    if Split.HELDOUT.value in data_root.resolve().parts or split is Split.HELDOUT:
        raise Refused("held-out data is never sent to a hosted backend")
    if split not in (Split.DEV, Split.M5FRESH):
        raise Refused(f"no hosted allowance for the {split.value} split")
    outside = sorted(set(scenario_ids) - manifest_ids(split, manifest_dir))
    if outside:
        raise Refused(f"hosted backends receive {split.value} scenarios only; {len(outside)} not in the "
                      f"{split.value} manifest")


def fresh_slice(manifest_dir: Path, k: int) -> tuple[str, ...]:
    """Slice ``k`` (1-6) of the fresh split: 10 consecutive IDs in the frozen manifest's order. Never printed."""
    if not 1 <= k <= FRESH_SLICES:
        raise Refused(f"--slice must be 1 to {FRESH_SLICES}")
    path = manifest_dir / f"{Split.M5FRESH.value}.json"
    if not path.is_file():
        raise Refused("no m5fresh manifest; the fresh split has not been generated")
    ids = json.loads(path.read_text(encoding="utf-8"))["scenario_ids"]
    if len(ids) != FRESH_SLICES * FRESH_SLICE_SIZE or len(set(ids)) != len(ids):
        raise Refused(f"the m5fresh manifest must list {FRESH_SLICES * FRESH_SLICE_SIZE} distinct scenarios")
    return tuple(ids[(k - 1) * FRESH_SLICE_SIZE:k * FRESH_SLICE_SIZE])


def collides_with_frozen_splits(scenario_ids: Sequence[str], manifest_dir: Path) -> bool:
    """A4 (2026-10-29): the fresh split's ID-collision check, using only the data guard's membership sets."""
    ids = set(scenario_ids)
    return any(ids & manifest_ids(split, manifest_dir) for split in (Split.DEV, Split.HELDOUT))


def run_rows(trace_dir: Path, data_root: Path, num_ctx: int) -> list[dict[str, Any]]:
    rows, seen = [], set()
    for path in sorted(trace_dir.glob("*.jsonl")):
        events = read_trace(path)
        start = next(e for e in events if e["event"] == "start")
        stop = next((e for e in events if e["event"] == "stop"), None)
        sid = start["scenario_id"]
        variant = "twin" if sid in seen else "original"
        seen.add(sid)
        root = data_root / TWINS_DIR if variant == "twin" else data_root
        truth = GroundTruth.model_validate_json((root / "ground_truth" / f"{sid}.json").read_text(encoding="utf-8"))
        obs = load_observable(root / "scenarios" / sid)
        existing = {obs.alert.source_id, *(r.source_id for records in (obs.logs, obs.metrics, obs.deployments,
                                                                       obs.config_changes, obs.dependencies)
                                           for r in records)}
        report = stop["report"] if stop else None
        cited = [i for h in (report or {}).get("hypotheses", []) for i in (*h["supporting_evidence"],
                                                                          *h["contradicting_evidence"])]
        pairs = [(h["service"], h["fault_type"]) for h in (report or {}).get("hypotheses", [])]
        answer = (truth.diagnosis.service.value, truth.diagnosis.fault_type.value)
        model_calls = [e for e in events if e["event"] == "tool" and not e.get("by_loop")]
        model_turns = [e for e in events if e["event"] == "model"]
        rows.append({
            "run": len(rows) + 1, "trace": path.name, "scenario_id": sid, "variant": variant, "tier": truth.tier.value,
            "injected": truth.injection is not None,
            "stop_reason": stop["stop_reason"] if stop else "error", "final_state": stop.get("state") if stop else None,
            "report_valid": report is not None,
            "repaired": any(e["event"] == "claim_check" and e.get("repaired") for e in events),
            "tool_calls": stop["tool_calls"] if stop else None, "turns": len(model_turns),
            "model_calls": len(model_calls), "valid_calls": sum(e["valid"] for e in model_calls),
            "timeouts": sum(e.get("error") == "timeout" for e in model_turns),
            "elapsed_s": stop["elapsed_s"] if stop else None,
            "wait_s": round(sum(e.get("wait_s") or 0.0 for e in model_turns), 3),
            "retries": sum(e.get("retries") or 0 for e in model_turns),
            "elapsed_ex_wait_s": (stop["elapsed_s"] - sum(e.get("wait_s") or 0.0 for e in model_turns)) if stop else None,
            "prompt_tokens": sum(e.get("prompt_tokens") or 0 for e in model_turns),
            "completion_tokens": sum(e.get("completion_tokens") or 0 for e in model_turns),
            "cited": len(cited), "cited_existing": sum(i in existing for i in cited),
            "top1": bool(pairs) and pairs[0] == answer, "top3": answer in pairs[:3],
            "top": list(pairs[0]) if pairs else None,
            **{f"investigated_{k}" if not k.startswith("investigated") else k: v
               for k, v in investigated(events, existing, num_ctx).items()},
            **shallow_measures(events),
        })
    return rows


def apply_agent_rule(rows: list[dict[str, Any]], complete: bool, *, active_time: bool = False) -> dict[str, Any]:
    """The pre-registered M4 decision rule over the original (non-twin) runs. Server-log overflow evidence
    (stage B) is applied on top in the write-up and overrides the trace-based overflow count.

    ``active_time`` (hosted backends, user decision 2026-10-28/29): the median-time thresholds apply to active time
    (wall time minus the provider's rate-limit waits). On hosted backends that threshold always passes, so it is
    not evidence of quality. Local results are computed exactly as before."""
    core = [r for r in rows if r["variant"] == "original"]
    inv = sum(r["investigated"] for r in core)
    valid = sum(r["report_valid"] for r in core)
    overflows = sum(not r["investigated_f_no_overflow"] for r in core)
    walls = [r["elapsed_s"] for r in core if r["elapsed_s"] is not None]
    times = [r["elapsed_ex_wait_s"] for r in core if r.get("elapsed_ex_wait_s") is not None] if active_time else walls
    median = statistics.median(times) if times else None
    works = inv >= 6 and valid >= 8 and overflows == 0 and median is not None and median <= 900
    hosted = inv <= 3 or overflows > 0 or (median is not None and median > 1500)
    rule = {"n": len(core), "investigated": inv, "valid_reports": valid, "trace_overflow_runs": overflows,
            "median_wall_s": statistics.median(walls) if walls else None, "max_wall_s": max(walls, default=None),
            "complete": complete, "budgets": {"agent": 40, "rule_baseline": 52},
            "verdict": ("propose_hosted" if not complete else
                        "works_locally" if works else "propose_hosted" if hosted else "in_between")}
    if active_time:
        rule.update(time_basis="active", median_active_s=median,
                    time_note="hosted: the median active-time threshold always passes; not evidence of quality")
    return rule


def run_agent(client: LLMClient, backend: str, model: str, data_root: Path, out_dir: Path,
              scenario_ids: Sequence[str], manifest_dir: Path = DEFAULT_MANIFEST_DIR,
              bounds: AgentBounds = AgentBounds(), min_free_gb: float = MIN_FREE_GB,
              max_swap_growth_gb: float = MAX_SWAP_GROWTH_GB, stats: Any = None, progress: bool = False,
              clock: Callable[[], float] = time.monotonic, progress_stream: Any = None, attempt: int = 1,
              smoke: bool = False, prompt_version: str = "v1", twins: bool = True, split: Split = Split.DEV,
              fresh_slice_k: int | None = None) -> dict[str, Any]:
    if backend == "mock":
        check_mock_target(scenario_ids, out_dir)
    if backend in HOSTED_BACKENDS:
        check_hosted_target(data_root, scenario_ids, manifest_dir, split=split)
    if split is Split.M5FRESH and (twins or prompt_version != M5_AGENT_PROMPT):
        raise Refused(f"fresh-split agent runs are originals only, with prompt {M5_AGENT_PROMPT}")
    trace_dir = out_dir / "traces"
    if any(trace_dir.glob("*.jsonl")) or (out_dir / "run_log.jsonl").exists():
        raise OutputExists(f"{out_dir} already holds an attempt; use a new --attempt number")
    manifest = verify_split(split, data_root, manifest_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = stats or system_stats
    run_twins = twins
    twins = 0 if not run_twins else sum(GroundTruth.model_validate_json((data_root / "ground_truth" / f"{sid}.json").read_text(
        encoding="utf-8")).injection is not None for sid in scenario_ids)
    unload = getattr(client, "unload", None)
    reporter = None
    if progress:
        reporter = Progress(len(scenario_ids) + twins, bounds.max_tool_calls, stats, out_dir, progress_stream)
        client = ProgressClient(client, reporter)
    inner = StateMachineInvestigator(client, bounds=bounds, traces=TraceWriter(trace_dir), clock=clock,
                                     prompt_version=prompt_version)
    guarded = GuardedInvestigator(inner, out_dir / "run_log.jsonl", out_dir, min_free_gb=min_free_gb,
                                  max_swap_growth_gb=max_swap_growth_gb, stats=stats, progress=reporter,
                                  after_run=unload)
    aborted: HarnessAbort | None = None
    try:
        run_split(guarded, split, data_root, manifest_dir=manifest_dir, scenario_ids=scenario_ids, twins=run_twins)
    except HarnessAbort as exc:
        aborted = exc
    rows = run_rows(trace_dir, data_root, bounds.num_ctx)
    complete = aborted is None and len(rows) == len(scenario_ids) + twins
    summary = {
        "metadata": {"backend": backend, "model": model, "client": client.describe(),
                     "prompt_sha256": prompt_sha256(prompt_version), "prompt_version": prompt_version, "twins": run_twins,
                     "bounds": asdict(bounds), "generator_version": manifest["generator_version"],
                     "manifest_sha256": manifest["content_sha256"], "git_commit": git_commit(),
                     "scenarios": list(scenario_ids), "attempt": attempt, "smoke": smoke, "split": split.value,
                     "slice": fresh_slice_k,
                     "aborted": None if aborted is None else str(aborted), "unload_between_runs": unload is not None,
                     "budgets_note": "M4 agent budget 40 read-tool calls; rule baseline uses ~52"},
        "runs": rows,
        "rule": apply_agent_rule(rows, complete, active_time=backend in HOSTED_BACKENDS),
    }
    if backend == "mock" or smoke or split is Split.M5FRESH:
        summary["rule"]["mechanics_check_only"] = summary["rule"].pop("verdict")
        summary["rule"]["verdict"] = ("not applicable (smoke run)" if smoke else "not applicable (mock backend)"
                                      if backend == "mock" else "not applicable (M5 reports the comparison only)")
    dump_json(out_dir / "summary.json", summary)
    (out_dir / "summary.md").write_text(summary_markdown(summary), encoding="utf-8", newline="\n")
    if aborted is not None:
        raise aborted
    return summary


def summary_markdown(summary: dict[str, Any]) -> str:
    m, rule = summary["metadata"], summary["rule"]
    lines = [f"# M4 agent: {m['backend']} ({m['model']}), attempt {m['attempt']}", ""]
    if m["backend"] == "mock":
        lines += ["**Mock backend: a scripted policy, not a model, on generated scenarios. Mechanics check only.**", ""]
    if m.get("aborted"):
        lines += [f"**Aborted: {m['aborted']}. Incomplete: counts as propose hosted.**", ""]
    lines += [f"Prompt sha256 `{m['prompt_sha256'][:12]}…`, code `{m['git_commit']}`. Budgets: agent 40 read-tool calls, "
              "rule baseline ~52. \"Investigated\" measures process, not insight. Counts, not rates.", "",
              "| Run | Scenario | Variant | Tier | Stop | Valid report | Investigated (a b c d e f) | Tool calls | "
              "Evidence calls | Kinds | Wall s | Max est / reported tokens | Max level | Top-1 |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in summary["runs"]:
        flags = "".join("y" if r[f"investigated_{k}"] else "n" for k in ("a_valid_report", "b_gather_evidence_calls",
                                                                          "c_data_kinds", "d_top_supported",
                                                                          "e_verified", "f_no_overflow"))
        wall = "–" if r["elapsed_s"] is None else f"{r['elapsed_s']:.1f}"
        lines.append(f"| {r['run']} | {r['scenario_id']} | {r['variant']} | {r['tier']} | {r['stop_reason']} | "
                     f"{'yes' if r['report_valid'] else 'no'} | {'yes' if r['investigated'] else 'no'} ({flags}) | "
                     f"{r['tool_calls']} | {r['evidence_calls']} | {', '.join(r['data_kinds']) or '–'} | {wall} | "
                     f"{r['max_estimated_tokens']} / {r['max_reported_prompt_tokens']} | {r['max_compaction_level']} | "
                     f"{'–' if r['top'] is None else r['top1']} |")
    waits = [r for r in summary["runs"] if r.get("wait_s")]
    if waits:
        lines += ["", "Provider rate-limit waits (counted in wall time): " + "; ".join(
            f"run {r['run']} {r['wait_s']:.1f} s over {r['retries']} retries, wall excluding waits "
            f"{r['elapsed_ex_wait_s']:.1f} s" for r in waits)]
    lines += ["", f"Rule: investigated {rule['investigated']}/{rule['n']}, valid reports {rule['valid_reports']}/{rule['n']}, "
              f"trace overflow runs {rule['trace_overflow_runs']}, median wall {rule['median_wall_s']}"
              + (f", median active {rule['median_active_s']} (the time thresholds use active time; on hosted "
                 "backends that always passes and is not evidence of quality)" if rule.get("time_basis") else "")
              + ". "
              f"**Verdict: {rule['verdict']}**", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sentinelops.evaluation.agent_run",
                                     description="M4 agent on the fixed dev set (ollama) or a generated set (mock).")
    parser.add_argument("--backend", choices=("mock", "ollama", "groq", "mistral"), required=True)
    parser.add_argument("--model", help="default: qwen3:4b (ollama), qwen/qwen3.8-27b (groq); "
                                        "mistral: required, the pinned dated model ID")
    parser.add_argument("--reasoning-effort", help="hosted: sent as reasoning_effort (groq default: none; "
                                                   "mistral: sent only if given)")
    parser.add_argument("--rpm", type=int, help="hosted: requests per minute to stay under (groq default 30; "
                                                "mistral: required, from the console)")
    parser.add_argument("--tpm", type=int, help="hosted: tokens per minute to stay under (groq default 8000; "
                                                "mistral: required, from the console)")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--data-root", type=Path, help="default: data/dev, or data/m5fresh with --split m5fresh")
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--smoke", metavar="SCENARIO_ID", help="ollama/groq: one dev scenario outside the core set")
    parser.add_argument("--set", choices=("core", "dev-gate"), default="core",
                        help="core: the 10 M4 core scenarios; dev-gate: the 22 pre-registered M5 dev scenarios")
    parser.add_argument("--prompt", choices=("v1", "v2"), default="v1", help="agent prompt version (v1 = d269d28d)")
    parser.add_argument("--no-twins", action="store_true", help="run originals only (M5 dev gate and headline)")
    parser.add_argument("--split", choices=(Split.DEV.value, Split.M5FRESH.value), default=Split.DEV.value,
                        help="m5fresh: the M5 headline, one fixed slice (--slice), mistral, prompt v1, originals only")
    parser.add_argument("--slice", type=int, help=f"m5fresh: slice 1-{FRESH_SLICES} of {FRESH_SLICE_SIZE} originals")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--min-free-gb", type=float, default=MIN_FREE_GB, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.attempt < 1:
        parser.error("--attempt must be at least 1")

    split = Split(args.split)
    if split is Split.M5FRESH:
        if args.backend != "mistral":
            parser.error("--split m5fresh runs on --backend mistral only")
        if args.smoke or args.set != "core":
            parser.error("--split m5fresh takes --slice, not --smoke or --set")
        if args.slice is None:
            parser.error(f"--split m5fresh needs --slice 1-{FRESH_SLICES}")
        if args.prompt != M5_AGENT_PROMPT:
            parser.error(f"v2 failed the dev gate; fresh-split runs use --prompt {M5_AGENT_PROMPT} only")
    elif args.slice is not None:
        parser.error("--slice is for --split m5fresh")
    data_root = args.data_root or Path("data") / split.value

    bounds = AgentBounds()
    try:
        if args.backend == "mock":
            if args.smoke:
                parser.error("--smoke is for the ollama backend")
            manifest = json.loads((args.manifest_dir / "dev.json").read_text(encoding="utf-8"))
            ids: Sequence[str] = manifest["scenario_ids"]
            client: LLMClient = DemoAgentPolicy()
            model = "scripted"
        else:
            if args.smoke and args.smoke in (*CORE_SCENARIOS, *PILOT_SCENARIOS):
                parser.error("--smoke must name a dev scenario outside the core and M3 pilot sets")
            if args.smoke and args.set != "core":
                parser.error("--smoke and --set are exclusive")
            ids = (fresh_slice(args.manifest_dir, args.slice) if split is Split.M5FRESH else (args.smoke,) if args.smoke
                   else M5_DEV_SCENARIOS if args.set == "dev-gate" else CORE_SCENARIOS)
            if args.backend == "groq":
                model = args.model or "qwen/qwen3.8-27b"
                client = OpenAICompatibleClient("groq", model, limits=RateLimits(args.rpm or 30, args.tpm or 8000),
                                                timeout_s=bounds.call_timeout_s, max_tokens=bounds.num_predict,
                                                extra={"reasoning_effort": args.reasoning_effort or "none"})
            elif args.backend == "mistral":
                if not (args.model and args.rpm and args.tpm):
                    parser.error("--backend mistral needs --model (the pinned dated ID) and --rpm and --tpm "
                                 "(from the console)")
                model = args.model
                extra = {"reasoning_effort": args.reasoning_effort} if args.reasoning_effort else {}
                client = OpenAICompatibleClient("mistral", model, limits=RateLimits(args.rpm, args.tpm),
                                                timeout_s=bounds.call_timeout_s, max_tokens=bounds.num_predict,
                                                extra=extra)
            else:
                model = args.model or "qwen3:4b"
                client = OllamaClient(model, base_url=args.ollama_url, timeout_s=bounds.call_timeout_s,
                                      num_ctx=bounds.num_ctx, think=False, num_predict=bounds.num_predict)
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", model)
        prefix = ("m5-fresh-" if split is Split.M5FRESH else "smoke-" if args.smoke
                  else "m5-dev-gate-" if args.set == "dev-gate" else "")
        suffix = (f"-prompt-{args.prompt}" if args.prompt != "v1" or args.set == "dev-gate" or split is Split.M5FRESH
                  else "") + (f"-slice{args.slice}" if split is Split.M5FRESH else "") + \
            (f"-attempt{args.attempt}" if args.attempt > 1 else "")
        name = f"{prefix}{args.backend}-{slug}{suffix}"
        out_dir = args.out_root / f"generator-v{GENERATOR_VERSION}" / name
        if args.backend == "mock":
            check_mock_target(ids, out_dir)
        summary = run_agent(client, args.backend, model, data_root, out_dir, ids, args.manifest_dir, bounds,
                            min_free_gb=args.min_free_gb, progress=not args.quiet, attempt=args.attempt,
                            smoke=bool(args.smoke), prompt_version=args.prompt,
                            twins=not args.no_twins and split is Split.DEV, split=split, fresh_slice_k=args.slice)
    except (Refused, DataMismatch, HarnessAbort, OutputExists, FileNotFoundError, MissingKey,
            DisallowedEndpoint) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(summary_markdown(summary))
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
