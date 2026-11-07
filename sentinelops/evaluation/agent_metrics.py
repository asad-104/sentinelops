"""Pre-registered M4 run measures (docs/PROGRESS.md, 2026-10-23): "investigated" (a)-(f) and the shallow-run
measures, computed from a run's trace events. "Investigated" measures process, not insight.

Criterion (e): at least one VERIFY read call, in either pass, tests rank 2 or tests a contradiction of
rank 1, against the ranking in force at the time of that call (the latest ``submit_hypotheses``). A call
qualifies only if it returned ok, is not an exact repeat of any earlier call in the run (same tool and
parsed arguments), and targets a service S (its ``service`` argument, or for ``get_record`` the
service of the returned record). It tests rank 2 if S is rank 2's service; it tests a contradiction of
rank 1 if S is rank 1's service and its data kind (logs, metrics or changes) is not among the kinds of
rank 1's cited IDs.
"""

from __future__ import annotations

import json
from typing import Any

from sentinelops.agent.context import EVIDENCE_KINDS, id_kind
from sentinelops.agent.machine import call_kind
from sentinelops.tools import TOOL_INPUT_MODELS


def _arguments(event: dict[str, Any]) -> dict[str, Any] | None:
    try:
        parsed = json.loads(event.get("arguments") or "{}")
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def criterion_e(events: list[dict[str, Any]]) -> dict[str, Any]:
    ranking: list[dict[str, Any]] | None = None
    seen: set[tuple[str, str]] = set()
    qualifying, considered = [], 0
    for e in events:
        if e["event"] == "hypotheses":
            ranking = e["ranking"]
            continue
        if e["event"] != "tool" or e["name"] not in TOOL_INPUT_MODELS:
            continue
        arguments = _arguments(e)
        signature = (e["name"], json.dumps(arguments, sort_keys=True) if arguments is not None else e["arguments"])
        repeat = signature in seen
        seen.add(signature)
        if e["state"] != "VERIFY" or e.get("by_loop") or arguments is None:
            continue
        considered += 1
        if not e["ok"] or repeat or not ranking:
            continue
        if e["name"] == "get_record":
            target = next((r["service"] for r in e.get("records", [])), None)
        else:
            target = arguments.get("service")
        if not target:
            continue
        rank1 = ranking[0]
        rank2 = ranking[1] if len(ranking) > 1 else None
        kinds1 = {id_kind(i) for i in (*rank1.get("supporting_evidence", ()), *rank1.get("contradicting_evidence", ()))}
        kind = call_kind(e["name"], arguments)
        tests_rank2 = rank2 is not None and target == rank2["service"]
        contradiction = target == rank1["service"] and kind in EVIDENCE_KINDS and kind not in kinds1
        if tests_rank2 or contradiction:
            qualifying.append({"call_id": e["call_id"], "turn": e["turn"],
                               "tests": "rank_2" if tests_rank2 else "contradiction_of_rank_1"})
    return {"met": bool(qualifying), "qualifying": qualifying, "verify_calls_considered": considered}


def investigated(events: list[dict[str, Any]], existing_ids: set[str], num_ctx: int) -> dict[str, Any]:
    """(a)-(f) as pre-registered. (f) here is the trace part; stage B adds the server log, which overrides it."""
    stop = next((e for e in events if e["event"] == "stop"), None)
    report = stop.get("report") if stop else None
    model_reads = [e for e in events if e["event"] == "tool" and not e.get("by_loop") and e["name"] in TOOL_INPUT_MODELS]
    gather_evidence = sum(e["state"] == "GATHER" and e.get("evidence") for e in model_reads)
    kinds = {r["kind"] for e in model_reads if e["ok"] for r in e.get("records", [])} & EVIDENCE_KINDS
    top = report["hypotheses"][0] if report else None
    top_cited = [i for i in (top or {}).get("supporting_evidence", []) if i in existing_ids]
    contexts = [e for e in events if e["event"] == "context"]
    over_budget = sum(e["estimated_tokens"] > e["budget"] for e in contexts)
    at_ctx = sum((e.get("prompt_tokens") or 0) >= num_ctx for e in events if e["event"] == "model")
    parts = {
        "a_valid_report": bool(stop and stop["stop_reason"] == "sufficient_evidence" and report),
        "b_gather_evidence_calls": gather_evidence >= 4,
        "c_data_kinds": len(kinds) >= 2,
        "d_top_supported": len(top_cited) >= 2 and any(not i.startswith("ALR-") for i in top_cited),
        "e_verified": criterion_e(events)["met"],
        "f_no_overflow": over_budget == 0 and at_ctx == 0,
    }
    return {**parts, "investigated": all(parts.values()), "gather_evidence_calls": gather_evidence,
            "evidence_kinds": sorted(kinds), "top_cited_existing": len(top_cited),
            "requests_over_budget": over_budget, "reported_at_num_ctx": at_ctx}


def shallow_measures(events: list[dict[str, Any]]) -> dict[str, Any]:
    reads = [e for e in events if e["event"] == "tool" and e["name"] in TOOL_INPUT_MODELS]
    model_reads = [e for e in reads if not e.get("by_loop")]
    services = set()
    for e in model_reads:
        arguments = _arguments(e) or {}
        if arguments.get("service"):
            services.add(arguments["service"])
    contexts = [e for e in events if e["event"] == "context"]
    models = [e for e in events if e["event"] == "model" and e.get("error") is None]
    discrepancies = 0
    by_turn = {e["turn"]: e for e in contexts}
    for m in models:
        c = by_turn.get(m["turn"])
        if c and m.get("prompt_tokens") and abs(c["estimated_tokens"] - m["prompt_tokens"]) > 0.15 * m["prompt_tokens"]:
            discrepancies += 1
    return {
        "read_calls": len(reads), "model_read_calls": len(model_reads),
        "evidence_calls": sum(bool(e.get("evidence")) for e in model_reads),
        "distinct_tools": len({e["name"] for e in model_reads}),
        "data_kinds": sorted({r["kind"] for e in model_reads if e["ok"] for r in e.get("records", [])} & EVIDENCE_KINDS),
        "services_examined": sorted(services),
        "states_visited": [e["state"] for e in events if e["event"] == "state_enter"],
        "max_compaction_level": max((e["level"] for e in contexts), default=None),
        "max_estimated_tokens": max((e["estimated_tokens"] for e in contexts), default=None),
        "max_reported_prompt_tokens": max((m.get("prompt_tokens") or 0 for m in models), default=None),
        "guard_fired": sum(bool(m.get("guard_fired")) for m in models),
        "estimate_discrepancies_over_15pct": discrepancies,
        "prompt_eval_s": [m.get("prompt_eval_s") for m in models],
    }
