"""M3 feasibility pilot, dev only: ``python -m sentinelops.evaluation.pilot --backend mock|ollama``.

Runs the pre-registered pilot set (docs/PROGRESS.md, 2026-10-23) through the
harness, which also runs the probe's injection twin. Before every run it checks
free disk, swap growth and the kernel memory-pressure level, and aborts the batch
past the thresholds. Reported numbers come from the run traces and dev ground
truth; the decision rule is applied as written. There is no split argument.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sentinelops.evaluation.harness import (
    CountingToolSet,
    DataMismatch,
    HarnessAbort,
    RunResult,
    git_commit,
    run_split,
)
from sentinelops.llm.client import ChatMessage, LLMClient, LLMError, LLMResponse, ToolSpec
from sentinelops.llm.loop import LoopBounds, ToolLoopInvestigator
from sentinelops.llm.mock import DemoPolicyClient
from sentinelops.llm.ollama import OllamaClient
from sentinelops.llm.prompt import prompt_sha256
from sentinelops.llm.trace import TraceWriter, read_trace
from sentinelops.report import InvestigationFailed, InvestigationReport
from sentinelops.scenario_files import dump_json, load_observable
from sentinelops.simulator.datasets import DEFAULT_MANIFEST_DIR, TWINS_DIR
from sentinelops.simulator.generator import GENERATOR_VERSION
from sentinelops.simulator.ground_truth import GroundTruth
from sentinelops.simulator.profiles import Split

# Fixed 2026-10-23: first dev scenario of each fault type in manifest order, then the injection probe
# (the harness runs its twin right after it).
CORE_SCENARIOS = ("sc-06b280fbed", "sc-1499febf6f", "sc-203fe8a4ca", "sc-2d438d4575", "sc-32aaf79bfd")
PROBE_SCENARIO = "sc-4141664f86"
PILOT_SCENARIOS = (*CORE_SCENARIOS, PROBE_SCENARIO)
DEFAULT_OUT_ROOT = Path("eval/pilot")
MIN_FREE_GB = 10.0
MAX_SWAP_GROWTH_GB = 2.0
CRITICAL_PRESSURE = 4  # kern.memorystatus_vm_pressure_level: 1 normal, 2 warn, 4 critical


def _sysctl(name: str) -> str | None:
    if platform.system() != "Darwin":
        return None
    try:
        return subprocess.run(["sysctl", "-n", name], capture_output=True, text=True, timeout=5,
                              check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def system_stats(path: Path) -> dict[str, Any]:
    """Read-only signals: free disk, swap used, kernel memory-pressure level (None where unavailable).
    Uses sysctl only; the ``memory_pressure`` command is never run (it applies pressure)."""
    swap = _sysctl("vm.swapusage") or ""
    used = re.search(r"used = ([\d.]+)M", swap)
    level = _sysctl("kern.memorystatus_vm_pressure_level")
    return {"free_disk_gb": round(shutil.disk_usage(path).free / 1e9, 2),
            "swap_used_mb": float(used.group(1)) if used else None,
            "pressure_level": int(level) if level and level.isdigit() else None}


class Progress:
    """Plain-text progress on stderr: one line per model turn, one summary line per run. Display only:
    it reads counters and stats and never changes the loop, traces or result files."""

    def __init__(self, total_runs: int, budget: int, stats: Any, disk_path: Path, stream: Any = None) -> None:
        self.total, self.budget, self.stats, self.disk_path = total_runs, budget, stats, disk_path
        self.stream = stream if stream is not None else sys.stderr
        self.run, self.turn, self.scenario_id, self.tools, self.started = 0, 0, "", None, 0.0

    def _write(self, text: str, final: bool = False) -> None:
        live = hasattr(self.stream, "isatty") and self.stream.isatty()
        if live:
            self.stream.write("\r\033[K" + text + ("\n" if final else ""))
        else:
            self.stream.write(text + "\n")
        self.stream.flush()

    def start_run(self, scenario_id: str, tools: CountingToolSet) -> None:
        self.run, self.turn, self.scenario_id, self.tools = self.run + 1, 0, scenario_id, tools
        self.started = time.monotonic()

    def on_turn(self) -> None:
        self.turn += 1
        now = self.stats(self.disk_path)
        swap = "–" if now["swap_used_mb"] is None else f"{now['swap_used_mb']:.0f} MB"
        used = len(self.tools.calls) if self.tools is not None else 0
        self._write(f"run {self.run}/{self.total} {self.scenario_id} | turn {self.turn} | tool calls "
                    f"{used}/{self.budget} | {time.monotonic() - self.started:.0f} s | swap {swap} | "
                    f"free disk {now['free_disk_gb']} GB")

    def end_run(self, stop_reason: str) -> None:
        self._write(f"run {self.run}/{self.total} {self.scenario_id} done: {stop_reason}, "
                    f"{time.monotonic() - self.started:.1f} s", final=True)


class ProgressClient:
    """Delegates every call to the real client unchanged, then reports the turn."""

    def __init__(self, inner: LLMClient, progress: Progress) -> None:
        self.inner, self.progress = inner, progress

    def chat(self, messages: list[ChatMessage], tools: list[ToolSpec]) -> LLMResponse | LLMError:
        response = self.inner.chat(messages, tools)
        self.progress.on_turn()
        return response

    def describe(self) -> dict[str, Any]:
        return self.inner.describe()


class GuardedInvestigator:
    """Checks disk and memory before each run and logs stats before and after it."""

    def __init__(self, inner: ToolLoopInvestigator, run_log: Path, disk_path: Path, *, min_free_gb: float,
                 max_swap_growth_gb: float, stats: Any = system_stats, progress: Progress | None = None) -> None:
        self.inner, self.name, self.progress = inner, inner.name, progress
        self.run_log, self.disk_path, self.stats = run_log, disk_path, stats
        self.min_free_gb, self.max_swap_growth_gb = min_free_gb, max_swap_growth_gb
        self.baseline = stats(disk_path)
        self._log({"event": "batch_start", **self.baseline})

    def _log(self, record: dict[str, Any]) -> None:
        with self.run_log.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    def _check(self, scenario_id: str) -> dict[str, Any]:
        now = self.stats(self.disk_path)
        reasons = []
        if now["free_disk_gb"] < self.min_free_gb:
            reasons.append(f"free disk {now['free_disk_gb']} GB < {self.min_free_gb} GB")
        if now["swap_used_mb"] is not None and self.baseline["swap_used_mb"] is not None and \
                now["swap_used_mb"] - self.baseline["swap_used_mb"] > 1000 * self.max_swap_growth_gb:
            reasons.append(f"swap grew by more than {self.max_swap_growth_gb} GB")
        if now["pressure_level"] is not None and now["pressure_level"] >= CRITICAL_PRESSURE:
            reasons.append("memory pressure is critical")
        if reasons:
            self._log({"event": "abort", "scenario_id": scenario_id, "reasons": reasons, **now})
            raise HarnessAbort("; ".join(reasons))
        return now

    def investigate(self, tools: CountingToolSet, scenario_id: str) -> InvestigationReport:
        self._log({"event": "run_start", "scenario_id": scenario_id, **self._check(scenario_id)})
        if self.progress:
            self.progress.start_run(scenario_id, tools)
        stop_reason = "error"
        try:
            report = self.inner.investigate(tools, scenario_id)
            stop_reason = report.stop_reason
            return report
        except InvestigationFailed as failed:
            stop_reason = failed.stop_reason
            raise
        finally:
            if self.progress:
                self.progress.end_run(stop_reason)
            self._log({"event": "run_end", "scenario_id": scenario_id, **self.stats(self.disk_path)})


def _cited(report: dict[str, Any] | None) -> list[str]:
    if not report:
        return []
    return [i for h in report["hypotheses"] for i in (*h["supporting_evidence"], *h["contradicting_evidence"])]


def run_rows(trace_dir: Path, data_root: Path) -> list[dict[str, Any]]:
    """One row per trace, in run order. The second trace of the probe scenario is its twin."""
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
        observable = load_observable(root / "scenarios" / sid)
        existing = {observable.alert.source_id, *(r.source_id for records in (
            observable.logs, observable.metrics, observable.deployments, observable.config_changes,
            observable.dependencies) for r in records)}
        model_calls = [e for e in events if e["event"] == "tool" and not e["by_loop"]]
        model_turns = [e for e in events if e["event"] == "model"]
        report = stop["report"] if stop else None
        cited = _cited(report)
        top = (report["hypotheses"][0]["service"], report["hypotheses"][0]["fault_type"]) if report else None
        rows.append({
            "run": len(rows) + 1, "trace": path.name, "scenario_id": sid, "variant": variant,
            "role": "probe" if sid == PROBE_SCENARIO else "core", "tier": truth.tier.value,
            "stop_reason": stop["stop_reason"] if stop else "error",
            "report_valid": report is not None,
            "repaired": any(e.get("repaired") for e in model_calls),
            "tool_calls": stop["tool_calls"] if stop else None,
            "model_calls": len(model_calls), "valid_calls": sum(e["valid"] for e in model_calls),
            "turns": len(model_turns), "model_errors": sum(e.get("error") is not None for e in model_turns),
            "elapsed_s": stop["elapsed_s"] if stop else None,
            "prompt_tokens": sum(e.get("prompt_tokens") or 0 for e in model_turns),
            "completion_tokens": sum(e.get("completion_tokens") or 0 for e in model_turns),
            "thinking_chars": sum(e.get("thinking_chars") or 0 for e in model_turns),
            "truncated_results": sum(e["truncated_for_context"] for e in model_calls),
            "cited": len(cited), "cited_existing": sum(i in existing for i in cited),
            "top1": None if top is None else top == (truth.diagnosis.service.value,
                                                     truth.diagnosis.fault_type.value),
            "top": None if top is None else list(top),
        })
    return rows


def apply_rule(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The pre-registered decision rule, over the core (non-probe) runs only."""
    core = [r for r in rows if r["role"] == "core"]
    calls, valid = sum(r["model_calls"] for r in core), sum(r["valid_calls"] for r in core)
    good = sum(r["stop_reason"] == "sufficient_evidence" and r["report_valid"] for r in core)
    cited, real = sum(r["cited"] for r in core), sum(r["cited_existing"] for r in core)
    walls = [r["elapsed_s"] for r in core if r["elapsed_s"] is not None]
    share = valid / calls if calls else 0.0
    citations = real / cited if cited else None
    median = statistics.median(walls) if walls else None
    feasible = (share >= 0.8 and good >= 4 and citations is not None and citations >= 0.9
                and median is not None and median <= 600)
    hosted = share < 0.6 or good <= 2 or (median is not None and median > 1200)
    return {"n_core": len(core), "valid_calls": [valid, calls], "valid_call_share": share,
            "sufficient_with_valid_report": good, "citations_real": [real, cited], "citation_share": citations,
            "median_wall_s": median,
            "verdict": "local_feasible" if feasible else "propose_hosted" if hosted else "in_between"}


def summary_markdown(summary: dict[str, Any]) -> str:
    m, rule = summary["metadata"], summary["rule"]
    lines = [f"# M3 pilot: {m['backend']} ({m['model']})", ""]
    if m["backend"] == "mock":
        lines += ["**Mock backend: a scripted policy, not a model. These numbers check the mechanics only and "
                  "say nothing about any model.**", ""]
    lines += [
        f"Generator {m['generator_version']}, data sha256 `{m['manifest_sha256'][:12]}…`, code `{m['git_commit']}`, "
        f"prompt sha256 `{m['prompt_sha256'][:12]}…`. Dev only. Counts, not rates: n = {rule['n_core']} core runs "
        "plus the injection probe pair. No pilot scenario is in the ambiguous tier, so the pilot says nothing "
        "about that tier. The 4,000-character cap on tool results can hide source IDs from the model.",
        "",
        "| Run | Scenario | Variant | Tier | Stop reason | Valid report | Valid calls | Turns | Wall s "
        "| Tokens (prompt / completion) | Thinking chars | Cited real | Top-1 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in summary["runs"]:
        wall = "–" if r["elapsed_s"] is None else f"{r['elapsed_s']:.1f}"
        lines.append(f"| {r['run']} | {r['scenario_id']} | {r['variant']} | {r['tier']} | {r['stop_reason']} "
                     f"| {'yes' + (' (repaired)' if r['repaired'] else '') if r['report_valid'] else 'no'} "
                     f"| {r['valid_calls']}/{r['model_calls']} | {r['turns']} | {wall} "
                     f"| {r['prompt_tokens']} / {r['completion_tokens']} | {r['thinking_chars']} "
                     f"| {r['cited_existing']}/{r['cited']} | {'–' if r['top1'] is None else r['top1']} |")
    share = rule["citation_share"]
    median = "–" if rule["median_wall_s"] is None else f"{rule['median_wall_s']:.1f} s"
    lines += [
        "",
        "## Decision rule (pre-registered 2026-10-23; core runs only; top-1 is not part of it)",
        f"- Valid tool calls: {rule['valid_calls'][0]}/{rule['valid_calls'][1]}",
        f"- Runs ending in sufficient_evidence with a valid report: {rule['sufficient_with_valid_report']}"
        f"/{rule['n_core']}",
        f"- Real citations: {rule['citations_real'][0]}/{rule['citations_real'][1]}"
        + ("" if share is not None else " (no citations)"),
        f"- Median wall time: {median}",
        f"- **Verdict: {rule['verdict']}**",
        "",
        f"Injection probe: {summary['probe']}",
        "",
    ]
    return "\n".join(lines)


def probe_note(rows: list[dict[str, Any]]) -> str:
    pair = [r for r in rows if r["role"] == "probe"]
    if len(pair) != 2:
        return "not run"
    original, twin = pair
    if original["top"] is None or twin["top"] is None:
        return "answer change not measurable (a run has no valid report)"
    return ("top-1 changed between original and twin" if original["top"] != twin["top"]
            else "top-1 unchanged between original and twin") + " (descriptive only, n = 1 pair)"


def build_client(args: argparse.Namespace, bounds: LoopBounds) -> LLMClient:
    if args.backend == "mock":
        return DemoPolicyClient()
    think = {"on": True, "off": False, "default": None}[args.think]
    return OllamaClient(args.model, base_url=args.ollama_url, timeout_s=bounds.call_timeout_s, think=think)


def run_pilot(client: LLMClient, backend: str, model: str, data_root: Path, out_dir: Path,
              manifest_dir: Path = DEFAULT_MANIFEST_DIR, bounds: LoopBounds = LoopBounds(),
              min_free_gb: float = MIN_FREE_GB, max_swap_growth_gb: float = MAX_SWAP_GROWTH_GB,
              stats: Any = None, smoke: str | None = None, progress: bool = False,
              clock: Callable[[], float] = time.monotonic, progress_stream: Any = None) -> dict[str, Any]:
    """``smoke``: run only this one non-pilot scenario, to check the client and tool-call parsing.
    A smoke run is never scored against the decision rule."""
    if smoke is not None and smoke in PILOT_SCENARIOS:
        raise ValueError("the smoke scenario must not be in the pilot set")
    """``stats`` defaults to ``system_stats`` (looked up at call time, so tests can replace it)."""
    trace_dir = out_dir / "traces"
    for stale in (*trace_dir.glob("*.jsonl"), out_dir / "run_log.jsonl"):
        stale.unlink(missing_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = stats or system_stats
    ids = PILOT_SCENARIOS if smoke is None else (smoke,)
    reporter = None
    if progress:
        twins = sum(GroundTruth.model_validate_json((data_root / "ground_truth" / f"{sid}.json").read_text(
            encoding="utf-8")).injection is not None for sid in ids if (data_root / "ground_truth" /
                                                                        f"{sid}.json").is_file())
        reporter = Progress(len(ids) + twins, bounds.max_tool_calls, stats, out_dir, progress_stream)
        client = ProgressClient(client, reporter)
    inner = ToolLoopInvestigator(client, bounds=bounds, traces=TraceWriter(trace_dir), clock=clock)
    guarded = GuardedInvestigator(inner, out_dir / "run_log.jsonl", out_dir, min_free_gb=min_free_gb,
                                  max_swap_growth_gb=max_swap_growth_gb, stats=stats, progress=reporter)
    result: RunResult = run_split(guarded, Split.DEV, data_root, manifest_dir=manifest_dir, scenario_ids=ids)
    rows = run_rows(trace_dir, data_root)
    summary = {
        "metadata": {"backend": backend, "model": model, "client": client.describe(),
                     "prompt_sha256": prompt_sha256(), "bounds": asdict(bounds),
                     "generator_version": result.metadata["generator_version"],
                     "manifest_sha256": result.metadata["manifest_sha256"], "git_commit": git_commit(),
                     "scenarios": list(PILOT_SCENARIOS) if smoke is None else [smoke], "smoke": smoke is not None},
        "runs": rows,
        "rule": apply_rule(rows),
        "probe": probe_note(rows),
    }
    if backend == "mock" or smoke is not None:  # the rule is for the pilot set run by a model
        summary["rule"]["mechanics_check_only"] = summary["rule"].pop("verdict")
        summary["rule"]["verdict"] = "not applicable (smoke run)" if smoke else "not applicable (mock backend)"
    dump_json(out_dir / "summary.json", summary)
    (out_dir / "summary.md").write_text(summary_markdown(summary), encoding="utf-8", newline="\n")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sentinelops.evaluation.pilot",
                                     description="M3 feasibility pilot on the fixed dev scenarios.")
    parser.add_argument("--backend", choices=("mock", "ollama"), required=True)
    parser.add_argument("--model", default="qwen3:4b", help="Ollama model tag (ignored for mock)")
    parser.add_argument("--think", choices=("default", "on", "off"), default="default",
                        help="Ollama thinking mode; 'default' leaves it to the server")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--data-root", type=Path, default=Path("data/dev"))
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR, help=argparse.SUPPRESS)
    parser.add_argument("--min-free-gb", type=float, default=MIN_FREE_GB, help=argparse.SUPPRESS)
    parser.add_argument("--quiet", action="store_true", help="no progress display on stderr")
    parser.add_argument("--smoke", metavar="SCENARIO_ID",
                        help="run one non-pilot dev scenario only (client check; never scored)")
    args = parser.parse_args(argv)

    bounds = LoopBounds()
    model = "scripted" if args.backend == "mock" else args.model
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", model)
    prefix = "smoke-" if args.smoke else ""
    out_dir = args.out_root / f"generator-v{GENERATOR_VERSION}" / f"{prefix}{args.backend}-{slug}"
    if args.smoke in PILOT_SCENARIOS:
        parser.error("--smoke must name a dev scenario outside the pilot set")
    try:
        summary = run_pilot(build_client(args, bounds), args.backend, model, args.data_root, out_dir,
                            args.manifest_dir, bounds, min_free_gb=args.min_free_gb, smoke=args.smoke,
                            progress=not args.quiet)
    except (DataMismatch, HarnessAbort) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(summary_markdown(summary))
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
