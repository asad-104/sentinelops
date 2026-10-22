# SentinelOps progress

## Current milestone
**M2: difficulty tiers, dev/held-out split, rule-based baseline, evaluation harness.** Not started; waiting for approval of M1.

## Completed milestones
- **M1: simulator, read-only tools, tests.** Verified 2026-10-22, 73 tests passing (`.venv/bin/python -m pytest`).
  - First pass diverged from the decided design (6 services incl. a database service, 4 fault types, no prompt injection, tools raised exceptions). Aligned in the same milestone.

## Decisions made
| Decision | Reason |
|---|---|
| 4 services, no DB service; pool health is `db_pool_utilization_pct` on auth/orders/payments | Decided design; keeps the system small while still allowing pool faults |
| Auth and payments have external dependencies (identity-provider, card-processor) in timeout logs only | Every service with a timeout setting needs something to time out against; keeps the 4-service graph |
| Scenarios stored as JSON/JSONL files, not a database | Deterministic, diffable, zero setup and cost; data volume is small |
| One `random.Random` per scenario, seeded from a string of (version, seed, index) | String seeding is stable across runs and independent of `PYTHONHASHSEED` |
| Fault types assigned in shuffled balanced blocks | Equal class counts without the fault being derivable from the index |
| Opaque scenario IDs (`sc-` + hash) | IDs reveal neither seed, index nor fault |
| Source IDs assigned after merge-and-sort | Position of an ID reveals nothing about the fault |
| Trigger chosen uniformly from already-drawn changes | Makes real and red-herring changes identically distributed by construction |
| Config trigger gets a harmful value | Legitimate diagnostic signal; documented as the only intended difference |
| Alert fires on the first post-onset breach of a 5-minute average, ~70% on a non-root service when one breaches | Realistic; the alerting service is often not the answer |
| Prompt injection in ~40% of scenarios, in the same template as benign payload logs, always claiming a wrong diagnosis | Tests that an investigator treats logs as data; a right claim would reward obeying it |
| `ToolSet.call` returns structured errors, never raises | An agent loop must be able to recover from bad calls |
| Truncation keeps earliest matches and reports `total_matches` | Simple and predictable; the agent narrows the window to page |
| argparse instead of typer for the CLI | No dependency needed for three flags |

## Known weaknesses
- With only 4 services, the gateway is upstream of everything and fires half the alerts (101/200, 50%, seed 7). The alert lands on the root service in 110/200 (55%), so "blame the alerting service" already gets the service right about half the time. A naive baseline will look better than it deserves; M2 should report this heuristic as a floor.
- Many faults are identifiable from a single distinctive log template (e.g. TLS errors means certificate expiry, OOM means memory leak). Without M2's ambiguous and missing-evidence tiers, the task may be too easy to separate the three approaches.
- Some symptoms only exist when a fault is present (e.g. `db.long_query`, `process.gc_pause`); a keyword baseline can exploit them. That is partly realistic, but it is a known shortcut.
- Metrics are smooth and propagation is a fixed halve-per-hop rule; real incidents are messier.
- "Time-window caps" is implemented as "must lie within the scenario window"; there is no maximum span per call.
- `internal_error` in `ToolSet.call` is a catch-all that could hide tool bugs; it is not exercised by a test.
- The simulator, future baseline and prompts are all written by the same author, so co-adaptation is a real risk.

## Open questions
- Should tool calls have a maximum query span (e.g. 60 minutes) to force the agent to narrow down, or is the scenario-window bound enough?
- Is it acceptable that the gateway often alerts, or should the alert service be balanced more across services?
- Should a too-small pool setting count as `config_error` (current) even though its symptoms look like `connection_pool_exhaustion`? The (service, fault) pair makes this a deliberate trap.

## Next action
User reviews M1. Then plan M2 (difficulty tiers, dev/held-out split by template variant and timing pattern, frozen held-out manifest hash, rule-based baseline on dev only, evaluation harness and metrics) and wait for approval before coding.
