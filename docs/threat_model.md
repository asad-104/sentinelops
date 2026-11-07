# Threat model

SentinelOps never touches a real system. It investigates synthetic incidents through read-only tools, so the threats are not to production infrastructure. They are to the **integrity of the evaluation** (labels leaking to the investigator, held-out data being contaminated, numbers being tuned to the test), to **API keys and account identifiers**, and to the **agent's judgement** when the data it reads contains instructions.

## Assets

| Asset | Why it matters |
|---|---|
| Ground truth (`data/<split>/ground_truth/`) | If an investigator can read the answer, every score is meaningless |
| The held-out split | It must stay unseen by development and by any hosted provider |
| The frozen manifests, prompts and pre-registration | They make the results checkable; silent changes would break that |
| Provider API keys and account IDs | Misuse costs money and exposes the account |
| The local machine | Model output must never run as code or commands |

## Trust boundaries

1. **Simulator → tools.**
   - Ground truth is written to separate files that no tool reads.
   - The tools package and the observable data models never import the simulator, and an AST-based test enforces that.
   - A tool loads one scenario by an ID matching `^sc-[0-9a-f]{10}$`, and the resolved path must stay inside the scenarios root.
   - Only the evaluation harness reads ground truth.
2. **Tool results → model.**
   - Log text is **untrusted**: about 40% of scenarios contain injected instructions in user-controlled log fields.
   - Tools return that text verbatim, as data.
   - In the agent's requests, tool results and ledger excerpts appear only in user and tool messages, never in the system message. Excerpts are capped in length and marked as data.
3. **Model → harness.**
   - Model output is validated before use: tool arguments by the same Pydantic models the tools use, reports by the report contract.
   - A tool not allowed in the current state returns a structured `wrong_state` error.
   - Citations must be IDs the model was actually shown. A fabricated ID gets one repair turn, then the run fails.
   - Every failure is a structured value that becomes an error row; nothing the model writes is executed.
4. **Local → hosted provider.**
   - A data guard allows only the dev split and the M5 fresh split to reach a hosted model. Held-out is refused in code, by path and by split name, before any file is read.
   - The client talks only to a registered provider's own HTTPS host, with no redirects.
   - The local Ollama client refuses any host that isn't loopback.
5. **Viewer → reader.**
   - The Streamlit viewer binds to `127.0.0.1` with telemetry off, and reads dev data and committed outputs only.
   - It refuses held-out paths, never lists fresh-split runs, and shows the fresh split only as aggregate counts.
   - Untrusted text is shown only in tables or code blocks, never rendered as Markdown or HTML.

## Read-only tools

There are nine tools, and all of them read:
- `get_alert`, `get_window`, `search_logs`, `get_metrics`, `list_deployments`, `list_config_changes`, `get_dependencies`, `get_timeline`, `get_record`.

None restarts, rolls back, writes, runs a shell command or makes a network call.

**Bounds:**
- every list tool has a capped `limit` and reports `truncated`;
- the agent has a 40-call budget, per-state caps, a timeout per model call, and a limit on total active time.

**Failures:** tools never raise. Every failure is `ok=False` with an error code.

**Remediation** is recommended in the report and never executed, because there is no tool that could execute it.

## The injection test: what it shows and what it doesn't

**How it works:**
- Each injected scenario has a **twin**: the same scenario with only the injected lines removed.
- In the safety test, the harness forces exposure: at the end of TRIAGE it issues one `search_logs` call per injected line, and the identical calls run on the twin.
- 21 pairs ran.

**Result:**
- top-1 changed between original and twin in 7 of 19 pairs with both reports;
- the original followed the injected claim in 1;
- the injected line was cited in 1;
- executed actions: 0.

**E1**, an exploratory replicate control decided after these counts, reran the originals once: 3 of 16 top-1 answers changed between identical reruns.

**What it shows:**
- Whether the agent's diagnosis moves when an injected instruction sits in its data, measured against a twin that isolates the injected lines.
- On this model and prompt, the changes could not be separated from run-to-run noise.

**What it does not show:**
- **Resistance in a system with action tools.** "Executed actions = 0" holds by design: no action tool exists. It is not a measured robustness property.
- **Resistance when the agent finds the injected text on its own.** Natural exposure was low: the agent was shown an injected line in 3 of 21 headline runs.
- **Other payload styles, placements, models or prompts.** The payloads are templated and author-written.
- **A robust estimate.** 19 pairs, one run each, and one replicate per original.

## Keys and account identifiers

- **Where keys live:**
  - Keys are read only from environment variables (`MISTRAL_API_KEY`, `GROQ_API_KEY`), set in the shell for a run and unset afterwards.
  - They are never written to a file, a trace or a summary.
  - The user runs every hosted batch in their own terminal.
- **Redaction:** provider error bodies and recorded rate-limit headers are passed through a redaction step that removes the key, `org_…` IDs and UUIDs before anything is stored.
- **Tests:**
  - offline: a fixture makes any network connection raise `NetworkBlocked`;
  - the providers are mocked;
  - tests use fake keys.
- **Repository:**
  - `.env` and `data/` are gitignored.
  - Run outputs were scanned for key patterns and account IDs before each commit.
  - The full history was scanned after the 2026-11-06 rewrite: no key patterns. One `org_…`-shaped value in `tests/test_openai_compat.py` appears to be a hand-written test fixture.

## Residual risks

- **Provider data retention:** the "no data retention" setting was set by the user and not verified, and the fresh split was sent to the provider. Held-out never was.
- **Shared authorship:** the simulator, baselines, prompts and injection payloads share one author, so the threats tested are the ones the author thought of.
- **Supply chain:** dependencies are pinned (`requirements.txt`, `requirements-viewer.txt`) but not hash-verified.
- **Pre-registration:** it limits tuning to the test, but it doesn't remove the author's knowledge of the dev results (see deviation D1 in the report).
