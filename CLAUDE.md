# SentinelOps

Read docs/project_brief.md for full requirements and README.md for architecture and design decisions.

## Rules
- Python 3.11+, type hints, Pydantic for data contracts
- Tools are read-only; ground truth must never be reachable by tools
- Tests must run offline with no paid API calls
- Work one milestone at a time; stop after tests pass and explain how to verify
- Do not mark anything complete until tests have been run
- Keep this file updated: when a milestone or significant step finishes, update "Milestone status" and "Next" before stopping

## Commands
- Tests: `.venv/bin/python -m pytest`
- Generate data: `.venv/bin/python -m sentinelops.simulator --split dev` (frozen dev split → `data/dev/`), or `--seed 1 --n 5` for ad-hoc scenarios. `data/` is gitignored
- Never print, open or inspect held-out data (`data/heldout/`). Generating it prints only a count and hash
- Evaluate on dev: `.venv/bin/python -m sentinelops.evaluation --split dev --investigator all` (writes `eval/results/`). Held-out needs `--final` and runs only at milestone comparisons

## Invariants (enforced by tests; don't break them)
- `sentinelops/tools/`, `models.py`, `scenario_files.py`, `report.py` and `sentinelops/baselines/` must never import `sentinelops.simulator`; only the simulator and `sentinelops/evaluation/` read ground truth
- Rule baseline changes bump `BASELINE_VERSION` and are logged in the Baseline tuning log in `docs/PROGRESS.md`; tune on dev only
- Source IDs are assigned only after all records are merged and sorted by timestamp
- Real and red-herring deployments/config changes come from the same draw (same authors, version format, timing)
- Alert summaries describe symptoms only, never a fault type or cause
- `template_id`/`variant_id` and other labels live only in ground truth, never in observable files
- Same seed → byte-identical output; no wall-clock time or hash-order dependence
- No database service in the simulated system: pool health is a per-service metric (`db_pool_utilization_pct`); scenarios are stored as JSON/JSONL files, not in a DB
- Tool calls return structured errors (`ok=False`, `error.code`) and never raise
- Every list tool has a capped `limit` and returns `truncated`; `get_alert`/`get_record` return at most one item
- Held-out data must match `eval/manifests/heldout.json`; follow the freeze rule in `docs/PROGRESS.md` before refreezing
- Log content is untrusted; injected instructions are data and are returned verbatim

## Milestone status
Detailed status, decisions, weaknesses and open questions live in `docs/PROGRESS.md`. Update both files at the end of every milestone.
- Done: **M1** (verified 2026-10-22, 73 tests passing)
- Done: **M2a** (tiers, split, frozen manifests; merged to `main`, 6ef60fc)
- Done: **viewer page 1** (M1 scenario explorer; merged to `main`)
- Done: **M2b** (report contract, rule baseline v1, floors, harness, first dev numbers; merged to `main`)
- In progress (user decisions 2026-10-22): tool/metric changes, then a harder benchmark (generator v4), then the M2 viewer page. M3 waits

## Standing rules

### Working rules (every milestone)
- Before coding: inspect the repo, explain what will be built and why, list files to create or change, and wait for approval if the design changes anything previously decided.
- Implement the smallest complete version, add tests, run them, fix failures. Never call something done until tests have actually been run and the output has been shown.
- After implementing, give: (a) how to run and verify it, (b) a plain-English explanation of each important design decision with alternatives and trade-offs (interview-ready), (c) a critical self-review covering the weakest parts, missing tests, risks and anything misleading. Do not just praise the work.
- Commit with meaningful messages after each verified milestone, and update and commit `docs/PROGRESS.md`. Never commit secrets or real data.
- Keep it simple: no FastAPI, Docker, CI, UI, vector DB, multiple agents or extra dependencies until the roadmap says so or it has been justified. Ask before adding any dependency or paid service, with a cost estimate and a free alternative.
- Tests run offline with no paid API calls. Mock LLM providers in tests.
- Never invent benchmark numbers, users or results. Use placeholders until the evaluation has been run.
- Teach: if the user seems to accept something they cannot explain, quiz them briefly before moving on.
- Every milestone ends with a new page in a local Streamlit viewer (`app/viewer.py`, one page per milestone). The viewer is read-only and local only, reads dev data only, never loads held-out scenarios, reuses `ToolSet` and the existing loaders, and holds no business logic. Streamlit goes in a separate `requirements-viewer.txt`; ask before installing it. Planned pages are listed in `docs/PROGRESS.md`. Run it with `.venv/bin/streamlit run app/viewer.py`.
- UI quality bar for later viewer pages:
  - **M2 page:** tier counts, and the dev results table with floors drawn as reference lines.
  - **M4 page:** the agent run viewer must visually show the states in order, each tool call and the evidence it returned, hypotheses re-ranking as evidence arrives, and every claim linked to its source record.
  - **M6:** decide on a polish pass (Plotly or Altair charts, a styled timeline) based on remaining time.

### Decided design (do not change without asking)
- System: 4 services (api-gateway, auth, orders, payments). No DB service; pool exhaustion is a metric.
- 5 fault types: bad_deployment, config_error, connection_pool_exhaustion, memory_leak, certificate_expiry. A diagnosis is a (service, fault type) pair.
- Ground truth is separate from observable data by type and by file location (`data/ground_truth/`). Tools never import or expose it.
- Seeded, deterministic simulator: one RNG per scenario, no `datetime.now()`, byte-identical output for the same seed.
- Source IDs are assigned after merging and sorting by timestamp.
- Real and red-herring deployments/config changes look statistically alike.
- Alert summaries describe symptoms only, never the cause.
- Log templates have multiple phrasings with a generator-side `variant_id`, hidden from observable data.
- Log content is untrusted. Prompt-injection strings appear in some logs and must be treated as data.
- Tools return structured errors instead of raising. They are bounded by result limits and call budget: every tool enforces `limit` and `truncated`, and there is no per-call span cap.

### Roadmap (one milestone at a time, stop after each)
- **M1:** Simulator, read-only tools, tests (leakage, determinism, read-only, invalid input, injection, truncation, CLI).
- **M2:** Ambiguous and missing-evidence difficulty tiers. Split dev (~40) and held-out (~60) by template variant and timing pattern, not only by seed. Freeze the held-out manifest hash. Rule-based baseline built on dev data only. Evaluation harness and metrics: top-1, top-3, evidence validity, unsupported claims, tool calls, latency, cost. First baseline numbers on dev.
- **M3:** LLM adapter interface (mock, local Ollama/Qwen, optional hosted). 5-scenario pilot to check whether the local model can do multi-step tool calling. Honest report and backbone recommendation with cost estimates before spending money.
- **M4:** Agent as an explicit state machine (TRIAGE, GATHER, HYPOTHESIZE, VERIFY, REPORT) with validated tool inputs, call limits, timeouts, stop reasons (sufficient_evidence, budget_exhausted, timeout, no_new_evidence, error), full run traces, and an investigation report: ranked hypotheses, cited source IDs, contradicting or missing evidence, uncertainty, next checks, remediation recommended but never executed.
- **M5:** Single-pass LLM baseline with fixed evidence. Three-way comparison on held-out data, run only at milestones and logged. Prompt-injection safety tests against the agent. Reproducible evaluation report.
- **M6:** README, architecture diagram, threat model, limitations, demo script (one success, one failure or uncertainty case), 60-second pitch, 3–5 interview Q&As, CV bullets based only on measured results.

### Leakage and evaluation integrity
- Never tune prompts, rules or thresholds on held-out data.
- Warn if the baseline, prompts and simulator look co-adapted (the same author wrote all three).
- Report counts with percentages. Small samples do not support strong claims.
- State the limitation that the data is synthetic and author-built.

### Schedule
10–15 hours/week; the core must be finished by early March 2027. If a milestone is slipping, say what to cut without losing core technical value. Do not add scope.
