"""Criterion (e) and "investigated" (a)-(f) on hand-built traces: met, not met and boundary cases.
"Investigated" measures process, not insight."""

from __future__ import annotations

import json

from sentinelops.evaluation.agent_metrics import criterion_e, investigated, shallow_measures

RANK = [{"rank": 1, "service": "orders", "fault_type": "memory_leak", "supporting_evidence": ["LOG-00001", "LOG-00002"],
         "contradicting_evidence": []},
        {"rank": 2, "service": "auth", "fault_type": "config_error", "supporting_evidence": ["LOG-00003"],
         "contradicting_evidence": []}]


def tool(state: str, name: str, args: dict, *, ok: bool = True, by_loop: bool = False, records=(), evidence=None,
         turn: int = 1, call_id: str = "c") -> dict:
    recs = [{"id": i, "kind": {"LOG": "logs", "MET": "metrics", "DPL": "changes", "CFG": "changes",
                              "ALR": "alert"}[i[:3]], "service": s} for i, s in records]
    return {"event": "tool", "state": state, "name": name, "arguments": json.dumps(args), "ok": ok, "by_loop": by_loop,
            "records": recs, "evidence": bool(recs) if evidence is None else evidence, "turn": turn, "call_id": call_id,
            "valid": True, "error_code": None if ok else "not_found"}


def hyps(ranking=RANK) -> dict:
    return {"event": "hypotheses", "ranking": ranking}


# Criterion (e)

def test_e_met_by_a_call_on_rank_two_service() -> None:
    events = [hyps(), tool("VERIFY", "search_logs", {"service": "auth", "limit": 5}, records=[("LOG-00010", "auth")])]
    result = criterion_e(events)
    assert result["met"] and result["qualifying"][0]["tests"] == "rank_2"


def test_e_met_by_a_contradiction_check_in_an_uncited_data_kind() -> None:
    events = [hyps(), tool("VERIFY", "get_metrics", {"service": "orders", "metric": "memory_pct"},
                           records=[("MET-00001", "orders")])]
    result = criterion_e(events)
    assert result["met"] and result["qualifying"][0]["tests"] == "contradiction_of_rank_1"


def test_e_not_met_by_more_of_the_same_kind_on_rank_one() -> None:
    events = [hyps(), tool("VERIFY", "search_logs", {"service": "orders", "limit": 9})]  # logs already cited for rank 1
    assert criterion_e(events)["met"] is False


def test_e_not_met_when_a_verify_call_repeats_an_earlier_gather_call() -> None:
    same = {"service": "auth", "limit": 5}
    events = [tool("GATHER", "search_logs", same), hyps(), tool("VERIFY", "search_logs", same)]
    assert criterion_e(events)["met"] is False
    # the same target with different arguments is not a repeat
    events.append(tool("VERIFY", "search_logs", {"service": "auth", "limit": 6}))
    assert criterion_e(events)["met"] is True


def test_e_uses_the_ranking_in_force_at_the_time_of_the_call() -> None:
    reranked = [dict(RANK[1], rank=1), dict(RANK[0], rank=2)]  # auth now rank 1, orders rank 2
    events = [hyps(), hyps(reranked), tool("VERIFY", "search_logs", {"service": "auth", "limit": 7})]
    # under the new ranking, auth is rank 1 and logs are cited for it: neither test applies
    assert criterion_e(events)["met"] is False
    before = [hyps(), tool("VERIFY", "search_logs", {"service": "auth", "limit": 7}), hyps(reranked)]
    assert criterion_e(before)["met"] is True  # the same call before the re-rank tested rank 2


def test_e_get_record_targets_the_returned_records_service() -> None:
    events = [hyps(), tool("VERIFY", "get_record", {"source_id": "DPL-002"}, records=[("DPL-002", "orders")])]
    assert criterion_e(events)["qualifying"][0]["tests"] == "contradiction_of_rank_1"  # changes not cited for rank 1
    events = [hyps(), tool("VERIFY", "get_record", {"source_id": "LOG-00009"}, records=[("LOG-00009", "orders")])]
    assert criterion_e(events)["met"] is False  # logs are cited for rank 1


def test_e_boundaries_failed_calls_other_states_no_ranking_no_target() -> None:
    assert not criterion_e([hyps(), tool("VERIFY", "search_logs", {"service": "auth"}, ok=False)])["met"]
    assert not criterion_e([hyps(), tool("GATHER", "search_logs", {"service": "auth"})])["met"]
    assert not criterion_e([tool("VERIFY", "search_logs", {"service": "auth"})])["met"]  # no ranking yet
    assert not criterion_e([hyps(), tool("VERIFY", "get_timeline", {})])["met"]  # no service targeted
    one = [RANK[0]]
    assert not criterion_e([hyps(one), tool("VERIFY", "search_logs", {"service": "auth"})])["met"]  # no rank 2


def test_e_counts_either_verify_pass() -> None:
    events = [hyps(), tool("VERIFY", "search_logs", {"service": "orders", "limit": 2}),
              {"event": "state_enter", "state": "GATHER"}, tool("GATHER", "list_deployments", {}),
              hyps(), tool("VERIFY", "search_logs", {"service": "auth", "limit": 3}, turn=9, call_id="second")]
    result = criterion_e(events)
    assert result["met"] and result["qualifying"] == [{"call_id": "second", "turn": 9, "tests": "rank_2"}]


# "Investigated" (a)-(f)

def _run(*, report=True, gather=4, kinds=("LOG", "MET"), top_ids=("LOG-00001", "MET-00001"), verify=True,
         reported=3000) -> list[dict]:
    events = [tool("TRIAGE", "get_alert", {}, by_loop=True, records=[("ALR-001", "orders")])]
    for i in range(gather):
        prefix = kinds[i % len(kinds)]
        events.append(tool("GATHER", "search_logs" if prefix == "LOG" else "get_metrics", {"limit": i + 1},
                           records=[(f"{prefix}-0000{i + 1}", "orders")]))
    events.append(hyps())
    if verify:
        events.append(tool("VERIFY", "search_logs", {"service": "auth", "limit": 99}, records=[("LOG-00090", "auth")]))
    events += [{"event": "context", "turn": 1, "estimated_tokens": 5000, "budget": 6144, "level": 0},
               {"event": "model", "turn": 1, "prompt_tokens": reported, "error": None}]
    top = {"rank": 1, "service": "orders", "fault_type": "memory_leak", "supporting_evidence": list(top_ids),
           "contradicting_evidence": []}
    events.append({"event": "stop", "stop_reason": "sufficient_evidence" if report else "timeout",
                   "report": {"hypotheses": [top]} if report else None})
    return events


EXISTING = {"ALR-001", "LOG-00001", "LOG-00003", "MET-00001", "MET-00002", "MET-00004", "LOG-00090"}


def test_investigated_all_met() -> None:
    result = investigated(_run(), EXISTING, 8192)
    assert result["investigated"] is True and all(result[k] for k in result if k[:2] in ("a_", "b_", "c_", "d_", "e_", "f_"))


def test_each_criterion_can_fail_alone() -> None:
    assert investigated(_run(report=False), EXISTING, 8192)["a_valid_report"] is False
    assert investigated(_run(gather=3), EXISTING, 8192)["b_gather_evidence_calls"] is False
    assert investigated(_run(kinds=("LOG",)), EXISTING, 8192)["c_data_kinds"] is False
    assert investigated(_run(top_ids=("ALR-001", "LOG-00001")), EXISTING, 8192)["d_top_supported"] is True
    assert investigated(_run(top_ids=("ALR-001",)), EXISTING, 8192)["d_top_supported"] is False
    assert investigated(_run(top_ids=("LOG-00001", "LOG-77777")), EXISTING, 8192)["d_top_supported"] is False
    assert investigated(_run(verify=False), EXISTING, 8192)["e_verified"] is False
    assert investigated(_run(reported=8192), EXISTING, 8192)["f_no_overflow"] is False
    for broken in (_run(report=False), _run(gather=3), _run(verify=False), _run(reported=9000)):
        assert investigated(broken, EXISTING, 8192)["investigated"] is False


def test_gather_calls_without_new_ids_are_not_evidence() -> None:
    events = _run()
    for e in events:
        if e["event"] == "tool" and e["state"] == "GATHER":
            e["evidence"] = False
    assert investigated(events, EXISTING, 8192)["b_gather_evidence_calls"] is False


def test_shallow_measures_count_calls_tools_kinds_and_services() -> None:
    m = shallow_measures(_run())
    assert m["model_read_calls"] == 5 and m["evidence_calls"] == 5
    assert m["distinct_tools"] == 2 and m["data_kinds"] == ["logs", "metrics"]
    assert m["services_examined"] == ["auth"]
