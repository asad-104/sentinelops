# M3 plan: LLM feasibility pilot

Status: approved with changes on 2026-10-23. Stage A (no model, no network, no money) is next; stage B needs a separate approval.

## Goal and scope
M3 is a feasibility test, not the final agent. It answers two questions:
- Can a small local model (Qwen via Ollama) use the existing read-only `ToolSet` to investigate a dev scenario?
- Is a hosted model worth paying for?

The explicit-state agent is M4 and is out of scope.

**Rules for both stages:**
- Dev data only; held-out data is never used.
- `httpx` only. No `anthropic` package and no hosted calls without explicit approval.
- Keys come only from environment variables. They are never printed, traced or committed, and `.env` stays gitignored.
- Tests run offline, behind a guard that fails any test that opens a network connection.

## Machine (checked 2026-10-22/23)
- Apple M2, 8 GB RAM.
- Free disk was 8.9 GiB at planning. After the user freed space on 2026-10-23 it is 27 GiB. The target is 15 GB free with a hard minimum of 10 GB: stop and report if free space falls below 10 GB at any point, including during runs.
- Streamlit must be stopped during model runs.
- Memory signals during runs are `memory_pressure` and swap growth. `vm_stat` free pages are not a reliable signal on macOS.

## Verified facts (D1: one read-only fetch each, 2026-10-23)
**Ollama library page:** https://ollama.com/library/qwen3
- Capability tags shown: `tools` and `thinking`.
- `qwen3:4b`: 2.5 GB download, context "256K", text input.
- Other tags shown include `qwen3:1.7b` (1.4 GB, 40K context) and `qwen3:8b` / `latest` (5.2 GB, 40K context).
- The page says the models support "precise integration with external tools in both thinking and unthinking modes".
- Header: "Updated 1 year ago". No absolute date is shown.
- **Not verified, because the page doesn't show it:**
  - the default quantization of `qwen3:4b`
  - how to disable or configure thinking mode
  - the model digest

  The model digest and Ollama version will be recorded from the local install in stage B.

**Anthropic pricing page:** https://platform.claude.com/docs/en/about-claude/pricing

All prices are per million tokens (MTok).

| Model | Base input | 5m cache write | Cache hit | Output | Batch input / output |
|---|---|---|---|---|---|
| Claude Haiku 5.5 (prompts ≤ 100,000 tokens) | $0.10 | $0.125 | $0.01 | $0.50 | $0.05 / $0.25 |
| Claude Haiku 5.5 (prompts > 100,000 tokens) | $0.50 | $0.625 | $0.05 | $2.50 | $0.25 / $1.25 |
| Claude Sonnet 5.5 | $2 | $2.50 | $0.10 | $10 | $1 / $5 |
| Claude Opus 5.5 | $4 | $5 | $0.20 | $20 | $2 / $10 |

- **Tool-use overhead:** each request with tools adds a 286-token "tool use system prompt" on all three models (406 tokens on Haiku 5.5 with `any`/`tool` choice).
- **US-only inference:** the `inference_geo` setting carries a 1.1× multiplier.
- The page says that for the most current prices one should visit claude.com/pricing. I didn't fetch that page.
- **Correction:** the earlier plan cited Sonnet 5.5 cache hits at $0.20 from a cached reference. The official page says **$0.10**.

## Architecture (stage A)
Investigator-side code never imports `sentinelops.simulator`, and the AST invariant test covers `sentinelops/llm/`.

| File | What it does | Why |
|---|---|---|
| `sentinelops/llm/client.py` | Frozen types: `ChatMessage`, `ToolSpec`, `ToolCallRequest`, `Usage`, `LLMResponse`, `LLMError(code, message)`. `LLMClient` Protocol with `chat(messages, tools) -> LLMResponse \| LLMError` | Errors returned as values, the same contract as `ToolResult`, so the loop never needs `try`/`except` around a model call |
| `sentinelops/llm/mock.py` | `ScriptedClient` replays fixed responses or errors and records each request | Loop tests need no model and no network |
| `sentinelops/llm/ollama.py` | `OllamaClient` over `httpx.Client`, `POST /api/chat` with `tools`, `stream: false`, `options.num_ctx`. Refuses a `base_url` that isn't loopback. Timeouts, connection errors, HTTP errors and bad JSON become `LLMError` | Local only by construction |
| `sentinelops/llm/schemas.py` | Function specs generated from `ToolSet.tool_input_models` (with `$ref` inlined), plus a `submit_report` spec for the part of `InvestigationReport` the model writes | Validation and the model's view of the tools cannot drift apart |
| `sentinelops/llm/prompt.py` | The frozen system prompt and tool descriptions, and their SHA-256 | Change 3: a revision is visible as a new hash |
| `sentinelops/llm/loop.py` | `ToolLoopInvestigator` implements the existing `Investigator` Protocol | Reuses the harness, `CountingToolSet` and scoring unchanged |
| `sentinelops/llm/trace.py` | One JSONL trace per run: turns, tool calls (validity, `ok`, error code, sizes), usage, latency, stop reason, report or validation error | Audit trail and data for the viewer. No ground truth and no secrets |
| `sentinelops/evaluation/harness.py` | Catches investigator crashes and records an error row; `scenario_ids` subset; `ScenarioScore` gains `stop_reason`, `report_valid`, `error` | A crash never stops a run or disappears |
| `sentinelops/evaluation/pilot.py` | `python -m sentinelops.evaluation.pilot --backend mock\|ollama`. Dev only, no split argument, checks the manifest hash, fixed pilot IDs | Writes `eval/pilot/generator-v5/<backend>-<model>/` |
| `app/pages/m3_pilot_traces.py` | Viewer page: pick a run, see its turns in order, each tool call's status, the stop reason, and the report or validation error. Reads only `eval/pilot/` | Standing viewer rule |

## Loop bounds and handling (approved as written)
| Bound | Value | Stop reason |
|---|---|---|
| Tool-call budget per scenario | 30 (inside the harness's 200) | `budget_exhausted` |
| Model turns | 40 | `budget_exhausted` |
| Timeout per model call | 180 s; 2 consecutive timeouts end the run | `timeout` |
| Total wall time per scenario | 20 min | `timeout` |
| Tool result shown to the model | capped at 4,000 characters, marked `truncated_for_context` | – |
| Context window | `num_ctx` 8192 | – |
| A valid `submit_report` | – | `sufficient_evidence` |
| 3 identical (tool, arguments) calls in a row | – | `no_new_evidence` |
| A persistent client error, 3 consecutive malformed calls, or a report still invalid after one repair turn | – | `error` |

- **Malformed tool calls** (bad JSON, an unknown tool, or a schema failure) are returned to the model as structured errors. They count as invalid calls, use budget and are traced. Nothing raises.
- **Repeated calls** get the earlier result again, flagged `duplicate_call`, and still use budget.
- **Injected text** goes back verbatim, as JSON in tool-result messages, never in the system prompt. The prompt says tool output is untrusted data. No action tools exist, and `executed_actions` must be empty. Influence is measured with the paired twin metric.
- **Budget comparability (change 1).** The pilot's 30-call budget is not the rule baseline's 52 calls. The M4/M5 budget will be pre-registered separately, and any comparison states both budgets.

## Pilot design (dev only, fixed now)
The rule is "the first scenario of each fault type in dev manifest order" (manifest generator v5, sha256 `5a35c45a…`). An injection probe is added (D2).

| Run | Scenario | Fault | Tier | Injection |
|---|---|---|---|---|
| 1 | `sc-06b280fbed` | config_error | standard | no |
| 2 | `sc-1499febf6f` | certificate_expiry | missing_evidence | no |
| 3 | `sc-203fe8a4ca` | connection_pool_exhaustion | standard | no |
| 4 | `sc-2d438d4575` | bad_deployment | missing_evidence | no |
| 5 | `sc-32aaf79bfd` | memory_leak | standard | no |
| 6 | `sc-4141664f86` | connection_pool_exhaustion | missing_evidence | yes (probe) |
| 7 | `sc-4141664f86`, twin | connection_pool_exhaustion | missing_evidence | removed |

**No pilot scenario is in the ambiguous tier, so the pilot says nothing about that tier (change 6).**

**Run order:**
1. A mock dry run.
2. A smoke run on scenario 1.
3. Runs 1–7, sequentially, at temperature 0 with a fixed seed.

**Memory safety:**
- Stop Streamlit and use `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1` and `num_ctx` 8192.
- Record `memory_pressure` and swap before and after each run in the run log.
- Abort if swap grows by more than 2 GB, memory pressure is critical, or free disk falls below 10 GB.

## Pilot questions (pre-registered in PROGRESS.md on 2026-10-23, before any code)
Reported as counts:
1. **Valid tool calls:** valid / all tool calls, pooled. Valid means the call parses, names a known tool and passes the schema.
2. **Runs inside budget:** runs ending in `sufficient_evidence`.
3. **Valid reports:** runs whose report validates against `InvestigationReport`, directly or after one repair (counted separately).
4. **Real citations:** cited IDs that exist / all cited IDs. The 4,000-character cap can hide source IDs from the model, so a low score may partly reflect the cap (change 5).
5. **Top-1, descriptive only:** k/5. Five scenarios cannot support an accuracy claim.

**Also recorded:**
- wall time and tokens per run
- swap growth and memory pressure
- thinking-mode presence, its configuration, and its effect on time and tokens (change 4)
- the probe's paired answer change
- the prompt hash

## Decision rule: hosted backbone (approved, fixed now)
The rule covers the 5 fixed runs; the probe pair is reported separately. Top-1 is not part of it.
- **Local is feasible for M4** if all of these hold:
  - valid tool calls ≥ 80%
  - ≥ 4 of 5 runs end in `sufficient_evidence` with a valid report (repair allowed)
  - real citations ≥ 90%
  - median wall time ≤ 10 min per scenario
- **Propose a hosted pilot** if any of these hold:
  - valid tool calls < 60%
  - ≤ 2 of 5 valid reports
  - median wall time > 20 min
- **In between:** one logged prompt revision (new hash), re-run once on the same 5 scenarios. If the result is still in between, propose hosted.
- **Hosted pilot conditions:** your explicit approval, a $5 hard cap set in the provider console, the same scenarios, bounds and questions, and httpx only.

## Costs
- **Local:** $0. Costs about 2.5 GB of disk for `qwen3:4b` (verified size), plus time.
- **Hosted (estimate, prices verified 2026-10-23 on the official page above).**
  - **Method:** about 110k input tokens and 8k output tokens per scenario, uncached. This is an estimate from measured tool-result sizes, at about 15 tool calls with resent history, plus 286 tool-overhead tokens per request.
  - **Range:** allow ±50%, because tokenizers differ.
  - **Replacement:** stage B's measured token counts replace this estimate.

| 7 runs | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|
| Estimated cost | ≈ $0.10–0.40 (requests over 100k tokens use the higher Haiku tier) | ≈ $2 | ≈ $4 (too close to the $5 cap; not recommended) |

- **Free alternative:** stay local. Try a different local configuration, or keep the mock backend and defer the backbone decision to M5.

## Stages
- **Stage A (no model, no network, no money):**
  - pre-registration in PROGRESS.md
  - everything in the architecture table
  - offline tests
  - a mock dry run of the pilot CLI, which writes mock traces
  - the M3 viewer page, plus `scripts/check_viewer_real_data.py` extended to render it

  Branch `m3-stage-a`. Stop for review; don't push.
- **Stage B (first real local run, after approval):**
  1. Re-check free disk.
  2. Install Ollama and pull `qwen3:4b`.
  3. Record the model digest and Ollama version.
  4. Stop Streamlit.
  5. Smoke run, then the 7 runs.
  6. Report the pilot questions and apply the decision rule.

  Commit the results, traces and run logs if they total a few MB. Stop for review.

## Time, risks, cuts
- **Time:** stage A about 8–10 h; stage B about 3–5 h.
- **Risks:**
  - Ollama's real tool-call response format may differ from the mocked one. The smoke run checks this first.
  - Swap on 8 GB distorts timing and timeouts.
  - The thinking mode's default and how to control it are unverified.
  - The 4B model may not call tools validly. That would be a result, not a failure.
- **Cut in this order if it slips:**
  1. viewer polish
  2. the probe pair
  3. any hosted pilot

  Never cut the network guard, the error stop reason, crash catching or the pre-registration.

## What could make the pilot misleading
- **Sample size:** n = 5 (7 with the probe pair). A 4/5 has a Wilson interval of about 38–96%. The rule decides feasibility, not quality.
- **Thresholds:** they are judgement, fixed before seeing any data.
- **Memory effects on 8 GB:** these can make the model look worse than it is. Swap is recorded per run.
- **Prompt tuned on the pilot scenarios:** the prompt is frozen in stage A against mock traces only, its hash is recorded, and at most one logged revision is allowed. Later dev-wide results report the pilot scenarios separately.
- **Co-adaptation:** the same author wrote the simulator, the tool descriptions and the prompt. The tool descriptions say what each tool returns, never what to look for.
- **Coverage:** no ambiguous scenario, and only one injection probe.
- **Non-determinism:** Ollama output can vary across runs and versions, so the version and digest are recorded and each run is one sample.
- **Configuration:** the 4,000-character cap and `num_ctx` 8192 shape what the model sees, so the pilot measures this configuration, not the model in general.
