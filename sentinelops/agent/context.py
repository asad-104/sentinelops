"""Context management for the M4 agent: never send the server a conversation it would have to truncate.

Each request is rebuilt from structured state, stable content first (for the backend's prefix cache):
  1. system prompt (pinned)                    2. triage data: alert, window, dependencies
  3. evidence ledger, bounded view (data)      4. older tool results, compacted (data)
  5. recent tool calls and results             6. STAGE block from the harness (pinned, always last)
Untrusted text (ledger excerpts, tool results) only ever appears in user and tool messages, and is
JSON-encoded, so a payload cannot start a new line or imitate a ledger entry or the STAGE block.

Ledger (stage A design correction, docs/PROGRESS.md 2026-10-23): every source ID the model was shown
stays citable (citations are checked against the full seen set), but the *rendered* ledger is bounded:
per (kind, service) group a count with first and last ID plus the most recent N entries; metric points
as one summary line per (service, metric) series; and every ID cited in the current ranking. Only items
that fit in the shown (capped) tool result enter the ledger.

Two safeguards keep the prompt within budget (prompt_budget + num_predict == num_ctx, no slack):
  (a) a client-side estimate, chars / 3.1 x 1.15, that also never falls below what the server's own
      reported counts imply (characters per token observed so far);
  (b) a server-count guard: a reported prompt above 90% of num_ctx raises the compaction level for
      every later turn.
Compaction is deterministic (decision D7). If even the most compact level does not fit, the run stops
with ``context_exhausted`` rather than sending a request the server would truncate.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any

from sentinelops.agent import prompt
from sentinelops.agent.states import AgentBounds, State
from sentinelops.llm.client import ChatMessage, ToolCallRequest, ToolSpec

ID_KINDS = {"LOG": "logs", "MET": "metrics", "DPL": "changes", "CFG": "changes", "ALR": "alert",
            "DEP": "dependencies"}
EVIDENCE_KINDS = frozenset({"logs", "metrics", "changes"})
SOURCE_ID = re.compile(r"\b(?:LOG|MET|DPL|CFG|ALR|DEP)-\d{3,5}\b")
# Context revision 1 (2026-10-27): 3.6 -> 3.1. 3.6 was calibrated on log-heavy M3 turns; metric-heavy prompts
# tokenize at about 3.1 (M4 smoke run 2, run 1 turn 4: 19,167 chars, 6,176 reported, estimate 6,123 at 3.6).
CHARS_PER_TOKEN = 3.1
ESTIMATE_MARGIN = 1.15


def id_kind(source_id: str) -> str:
    return ID_KINDS.get(source_id.split("-", 1)[0], "other")


class ContextExhausted(Exception):
    """Even the most compact rendering exceeds the prompt budget."""


@dataclass(frozen=True)
class LedgerEntry:
    source_id: str
    kind: str
    service: str | None
    timestamp: str | None
    excerpt: str
    series: str | None = None  # "service/metric" for metric points
    value: float | None = None


def _excerpt(item: dict[str, Any]) -> str:
    if "message" in item:
        return str(item["message"])
    if "metric" in item and "value" in item:
        return f"{item['metric']}={item['value']}"
    if "version" in item:
        return f"deploy {item.get('previous_version')} -> {item['version']} by {item.get('author')}: {item.get('summary')}"
    if "key" in item:
        return f"config {item['key']}: {item.get('old_value')} -> {item.get('new_value')} by {item.get('author')}"
    if "caller" in item:
        return f"{item['caller']} -> {item['callee']}"
    return str(item.get("summary") or item.get("description") or "")


@dataclass(frozen=True)
class LedgerView:
    """How much of the ledger a compaction level renders (frozen parameters; see LEVELS)."""

    recent_per_group: int  # most recent N entries per (kind, service) group, in addition to cited IDs
    excerpt: int | None  # excerpt length for rendered entries; None = no excerpt
    series_detail: bool  # metric summaries with first/last timestamps
    max_series: int | None  # render only the most recently updated series (None = all)


class Ledger:
    """Every source ID the model was shown (the full seen set, all citable) and a bounded rendering of it."""

    def __init__(self) -> None:
        self.entries: dict[str, LedgerEntry] = {}

    def __contains__(self, source_id: object) -> bool:
        return source_id in self.entries

    def __len__(self) -> int:
        return len(self.entries)

    def add(self, items: list[dict[str, Any]], shown: str | None = None) -> list[str]:
        """Record items returned by a tool; with ``shown``, only items whose ID appears in the text the model
        was shown (the capped result). Returns the source IDs that were new."""
        new = []
        for item in items:
            sid = item.get("source_id")
            if not isinstance(sid, str) or (shown is not None and sid not in shown):
                continue
            if sid not in self.entries:
                service = item.get("service") or item.get("caller")
                kind = id_kind(sid)
                series = f"{service}/{item['metric']}" if kind == "metrics" and "metric" in item else None
                value = item.get("value") if series else None
                self.entries[sid] = LedgerEntry(sid, kind, service, item.get("timestamp"), _excerpt(item), series,
                                                value)
                new.append(sid)
        return new

    def render(self, view: LedgerView, cited: set[str]) -> str:
        lines = ["DATA evidence ledger (untrusted excerpts; one JSON object per line). All IDs you have been shown "
                 "are citable; this view lists group counts, recent entries, metric series and cited IDs:"]
        groups: dict[tuple[str, str | None], list[LedgerEntry]] = {}
        series: dict[str, list[LedgerEntry]] = {}
        for e in self.entries.values():
            if e.series:
                series.setdefault(e.series, []).append(e)
            else:
                groups.setdefault((e.kind, e.service), []).append(e)

        def entry_line(e: LedgerEntry) -> str:
            record: dict[str, Any] = {"id": e.source_id, "kind": e.kind, "service": e.service}
            if view.excerpt is not None:
                record["t"] = e.timestamp
                record["excerpt"] = e.excerpt[:view.excerpt]
            return json.dumps(record, sort_keys=True)

        for (kind, service), members in groups.items():
            lines.append(json.dumps({"group": f"{kind}/{service}", "seen": len(members), "first": members[0].source_id,
                                     "last": members[-1].source_id}, sort_keys=True))
            shown = members[-view.recent_per_group:] if view.recent_per_group else []
            shown_ids = {e.source_id for e in shown}
            for e in [m for m in members if m.source_id in cited and m.source_id not in shown_ids] + shown:
                lines.append(entry_line(e))
        ordered = sorted(series.items(), key=lambda kv: list(self.entries).index(kv[1][-1].source_id))
        if view.max_series is not None and len(ordered) > view.max_series:
            omitted = ordered[:-view.max_series]
            lines.append(json.dumps({"series_not_shown": len(omitted)}, sort_keys=True))
            ordered = ordered[-view.max_series:]
        for name, points in ordered:
            values = [p.value for p in points if isinstance(p.value, (int, float))]
            peak = max(points, key=lambda p: p.value if isinstance(p.value, (int, float)) else float("-inf"))
            record: dict[str, Any] = {"series": name, "points": len(points),
                                      "min": min(values) if values else None, "max": max(values) if values else None,
                                      "ids": list(dict.fromkeys([points[0].source_id, peak.source_id,
                                                                 points[-1].source_id]))}
            if view.series_detail:
                record["first_t"], record["last_t"] = points[0].timestamp, points[-1].timestamp
            lines.append(json.dumps(record, sort_keys=True))
            for p in points:
                if p.source_id in cited and p.source_id not in record["ids"]:
                    lines.append(entry_line(p))
        return "\n".join(lines)


@dataclass
class Exchange:
    """One model tool call and what the loop returned for it."""

    call: ToolCallRequest
    shown: str  # the full result text, already capped at result_char_cap
    summary: dict[str, Any] = field(default_factory=dict)  # tool, arguments, ok, error, counts, sample IDs, excerpts

    def compact(self, excerpt_cap: int | None) -> str:
        s = dict(self.summary)
        if excerpt_cap is None:
            s.pop("excerpts", None)
        else:
            s["excerpts"] = [x[:excerpt_cap] for x in s.get("excerpts", [])]
        return json.dumps(s, sort_keys=True)


@dataclass(frozen=True)
class Level:
    recent: int  # how many latest exchanges are shown in full
    recent_cap: int | None  # extra cap on each recent result (characters)
    compact_last: int | None  # render only the last M compacted exchanges (None = all), plus a count line
    compact_excerpt: int | None  # excerpt length in compacted results; None = no excerpts
    ledger: LedgerView


# Frozen 2026-10-23 (stage A design correction), set from the synthetic worst-case test only.
LEVELS: tuple[Level, ...] = (
    Level(recent=2, recent_cap=None, compact_last=None, compact_excerpt=120,
          ledger=LedgerView(recent_per_group=4, excerpt=100, series_detail=True, max_series=None)),
    Level(recent=1, recent_cap=None, compact_last=None, compact_excerpt=80,
          ledger=LedgerView(recent_per_group=3, excerpt=80, series_detail=True, max_series=None)),
    Level(recent=1, recent_cap=None, compact_last=12, compact_excerpt=40,
          ledger=LedgerView(recent_per_group=2, excerpt=40, series_detail=False, max_series=None)),
    Level(recent=1, recent_cap=1500, compact_last=6, compact_excerpt=None,
          ledger=LedgerView(recent_per_group=1, excerpt=None, series_detail=False, max_series=12)),
    Level(recent=0, recent_cap=None, compact_last=3, compact_excerpt=None,
          ledger=LedgerView(recent_per_group=1, excerpt=None, series_detail=False, max_series=6)),
)
MAX_LEVEL = len(LEVELS) - 1


class TokenEstimator:
    """Safeguard (a): chars / 3.1 x 1.15, and never below what the server's reported counts imply."""

    def __init__(self, chars_per_token: float = CHARS_PER_TOKEN, margin: float = ESTIMATE_MARGIN) -> None:
        self.chars_per_token, self.margin = chars_per_token, margin
        self.observed_chars_per_token: float | None = None

    def estimate(self, chars: int) -> int:
        estimate = math.ceil(chars / self.chars_per_token * self.margin)
        if self.observed_chars_per_token:
            estimate = max(estimate, math.ceil(chars / self.observed_chars_per_token))
        return estimate

    def observe(self, chars: int, reported_tokens: int | None) -> None:
        if not reported_tokens or chars <= 0:
            return
        ratio = chars / reported_tokens
        self.observed_chars_per_token = min(ratio, self.observed_chars_per_token or ratio)


@dataclass(frozen=True)
class BuiltRequest:
    messages: list[ChatMessage]
    chars: int
    estimated_tokens: int
    level: int
    rendered_ids: frozenset[str]
    components: dict[str, int]  # characters per component (for the token table)


def specs_chars(specs: list[ToolSpec]) -> int:
    return len(json.dumps([{"name": s.name, "description": s.description, "parameters": s.parameters}
                           for s in specs]))


def request_chars(messages: list[ChatMessage], specs: list[ToolSpec]) -> int:
    total = specs_chars(specs)
    for m in messages:
        total += len(m.content) + sum(len(c.name) + len(c.raw_arguments) for c in m.tool_calls)
    return total


class ContextBuilder:
    def __init__(self, bounds: AgentBounds, specs: list[ToolSpec], estimator: TokenEstimator | None = None) -> None:
        self.bounds, self.specs = bounds, specs
        self.estimator = estimator or TokenEstimator()
        self.min_level = 0  # raised (sticky) by the server-count guard
        self.guard_triggers = 0
        self.last_level = 0

    def stage_block(self, state: State, instruction: str, used: int, notes: list[str],
                    progress: dict[str, int] | None = None) -> str:
        """The harness-authored block, rendered from the hashed STAGE_TEMPLATE (agent/prompt.py)."""
        t = prompt.STAGE_TEMPLATE
        p = progress or {}
        lines = [t["header"].format(state=state.value),
                 t["budget"].format(used=used, budget=self.bounds.max_tool_calls)]
        if state is State.GATHER and "evidence" in p:
            lines.append(t["gather_progress"].format(evidence=p["evidence"], needed=self.bounds.min_gather_evidence))
        if state is State.VERIFY and "verify" in p:
            lines.append(t["verify_progress"].format(verify=p["verify"], cap=self.bounds.verify_cap,
                                                     needed=self.bounds.min_verify_reads))
        lines.append(t["instruction"].format(instruction=instruction))
        lines += [t["note"].format(note=n) for n in notes]
        lines.append(t["reply"])
        return "\n".join(lines)

    def render(self, level: int, system: str, triage: str, ledger: Ledger, exchanges: list[Exchange],
               stage: str, cited: set[str] = frozenset()) -> tuple[list[ChatMessage], dict[str, int]]:
        spec = LEVELS[level]
        parts: dict[str, int] = {"system": len(system), "triage": len(triage), "stage": len(stage),
                                 "tool_specs": specs_chars(self.specs), "ledger": 0, "compacted": 0, "recent": 0}
        messages = [ChatMessage("system", system), ChatMessage("user", triage)]
        if len(ledger):
            text = ledger.render(spec.ledger, set(cited))
            parts["ledger"] = len(text)
            messages.append(ChatMessage("user", text))
        cut = max(0, len(exchanges) - spec.recent)
        older, recent = exchanges[:cut], exchanges[cut:]
        if older:
            hidden = older if spec.compact_last is None else older[:-spec.compact_last]
            visible = older if spec.compact_last is None else older[-spec.compact_last:]
            lines = ["DATA earlier tool results, compacted (untrusted; one JSON object per line):"]
            if hidden and spec.compact_last is not None:
                lines.append(json.dumps({"earlier_calls_not_shown": len(hidden)}))
            lines += [x.compact(spec.compact_excerpt) for x in visible]
            text = "\n".join(lines)
            parts["compacted"] = len(text)
            messages.append(ChatMessage("user", text))
        for x in recent:
            shown = x.shown if spec.recent_cap is None else x.shown[:spec.recent_cap]
            parts["recent"] += len(shown) + len(x.call.name) + len(x.call.raw_arguments)
            messages.append(ChatMessage("assistant", "", tool_calls=(x.call,)))
            messages.append(ChatMessage("tool", shown, tool_name=x.call.name, tool_call_id=x.call.id))
        messages.append(ChatMessage("user", stage))
        return messages, parts

    def build(self, system: str, triage: str, ledger: Ledger, exchanges: list[Exchange], stage: str,
              cited: set[str] = frozenset()) -> BuiltRequest:
        for level in range(self.min_level, MAX_LEVEL + 1):
            messages, parts = self.render(level, system, triage, ledger, exchanges, stage, cited)
            chars = request_chars(messages, self.specs)
            estimate = self.estimator.estimate(chars)
            if estimate <= self.bounds.prompt_budget:
                self.last_level = level
                rendered = frozenset(i for m in messages for i in SOURCE_ID.findall(m.content))
                return BuiltRequest(messages, chars, estimate, level, rendered, parts)
        raise ContextExhausted(f"even compaction level {MAX_LEVEL} needs {estimate} estimated tokens "
                               f"(budget {self.bounds.prompt_budget})")

    def on_reported(self, chars: int, reported_tokens: int | None) -> bool:
        """Safeguard (b). Returns True if the guard fired (the next turn compacts harder)."""
        self.estimator.observe(chars, reported_tokens)
        if reported_tokens is not None and reported_tokens > self.bounds.server_guard_fraction * self.bounds.num_ctx:
            self.min_level = min(MAX_LEVEL, max(self.min_level, self.last_level + 1))
            self.guard_triggers += 1
            return True
        return False
