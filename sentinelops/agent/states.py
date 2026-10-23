"""States, allowed tools and transitions of the M4 agent (pre-registered in docs/PROGRESS.md, 2026-10-23).

TRIAGE → GATHER → HYPOTHESIZE → VERIFY → (back to GATHER at most once, then HYPOTHESIZE → VERIFY
again) → REPORT. The loop, not the model, owns the transitions: a state tool asks for one, and the
loop checks the precondition. Any tool not allowed in the current state is a ``wrong_state`` error.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sentinelops.tools import TOOL_INPUT_MODELS


class State(StrEnum):
    TRIAGE = "TRIAGE"
    GATHER = "GATHER"
    HYPOTHESIZE = "HYPOTHESIZE"
    VERIFY = "VERIFY"
    REPORT = "REPORT"


READ_TOOLS = frozenset(TOOL_INPUT_MODELS)
FINISH_GATHERING = "finish_gathering"
SUBMIT_HYPOTHESES = "submit_hypotheses"
RETURN_TO_GATHER = "return_to_gather"
FINISH_VERIFYING = "finish_verifying"
SUBMIT_REPORT = "submit_report"
STATE_TOOLS = (FINISH_GATHERING, SUBMIT_HYPOTHESES, RETURN_TO_GATHER, FINISH_VERIFYING, SUBMIT_REPORT)

# TRIAGE is issued by the loop (decision D8): the agent never decides how to begin.
TRIAGE_CALLS = ("get_alert", "get_window", "get_dependencies")

ALLOWED: dict[State, frozenset[str]] = {
    State.TRIAGE: frozenset(),
    State.GATHER: READ_TOOLS | {FINISH_GATHERING},
    State.HYPOTHESIZE: frozenset({SUBMIT_HYPOTHESES}),
    State.VERIFY: READ_TOOLS | {SUBMIT_HYPOTHESES, RETURN_TO_GATHER, FINISH_VERIFYING},
    State.REPORT: frozenset({SUBMIT_REPORT}),
}

# Every transition the loop may make. Anything else is a bug (tested).
TRANSITIONS: frozenset[tuple[State, State]] = frozenset({
    (State.TRIAGE, State.GATHER),
    (State.GATHER, State.HYPOTHESIZE),
    (State.HYPOTHESIZE, State.VERIFY),
    (State.VERIFY, State.GATHER),  # at most once per run
    (State.VERIFY, State.REPORT),
})


@dataclass(frozen=True)
class AgentBounds:
    """Pre-registered M4 bounds (decisions D2-D4)."""

    max_tool_calls: int = 40  # read-tool calls, TRIAGE's 3 included; state tools are free
    gather_first_pass_cap: int = 16
    verify_cap: int = 8  # both VERIFY passes together
    min_gather_evidence: int = 4  # before finish_gathering on the first pass
    min_verify_reads: int = 1  # before finish_verifying
    max_returns_to_gather: int = 1
    max_turns: int = 60
    call_timeout_s: float = 180.0  # enforced by the client; recorded here
    max_consecutive_timeouts: int = 2
    max_consecutive_client_errors: int = 2
    total_timeout_s: float = 1800.0
    max_consecutive_malformed: int = 3
    max_identical_calls: int = 3
    max_no_new_evidence: int = 3  # consecutive GATHER calls that returned no new source ID
    max_report_repairs: int = 1
    result_char_cap: int = 4000
    num_ctx: int = 8192
    num_predict: int = 2048
    prompt_budget: int = 6144  # estimated tokens; prompt_budget + num_predict == num_ctx, no slack
    server_guard_fraction: float = 0.9
