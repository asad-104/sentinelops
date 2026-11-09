# History rewrites (2026-11-06 and 2026-11-09)

The git history of this repository was first rewritten on 2026-11-06, to remove non-project text from two files: `docs/project_brief.md` and `CLAUDE.md`.

**The first rewrite (2026-11-06):**
- **Line-level:** at every commit, only the affected lines of those two files were edited, with the same edits at every commit. No other file changed at any commit.
- **Kept:** every commit's author, date, message and technical content.
- **Dropped:** `baa5edd`, the commit that had made this removal in the working tree. After the rewrite it changed nothing, so it became empty and was removed.
- **Tags and branches** were rewritten with the history.

**The second rewrite (2026-11-09): commit identity.**
- **What changed:** in every commit, the author and committer email, and the tagger email of `m3-complete`, `m4-complete` and `m5-complete`, went from a machine-default address to the GitHub noreply address of the same person. (`m2-complete` is a lightweight tag and has no tagger.)
- **Unchanged:** names, dates, messages (co-author trailers included) and every tree. No commit was dropped.
- **Hashes:** every commit hash changed again.

**Reading hashes:**
- **Docs:** hash citations in `docs/` and `CLAUDE.md` use the final hashes, updated in the commit that added this version of the note.
- **Commit messages** were updated automatically by both rewrites.
- **Run metadata keeps the hashes it recorded at run time,** all from before the first rewrite: the `git_commit` fields and "code" lines in `eval/` summaries, and `run_commits` in the M5 analysis. Read them through the table's first column.
- **One code comment** (`sentinelops/evaluation/agent_run.py`, "report `c1db227`") cites an intermediate hash. Read it through the table's second column.
- **Trees:** the second rewrite changed no file: the tree of every commit is byte-identical before and after it. The first rewrite changed only the lines described above.
- **Backup:** full bundles of the history before each rewrite are kept outside the repository.

## Tags (final)

| Tag | Commit |
|---|---|
| `m2-complete` | `925d43a` |
| `m3-complete` | `c8b1e70` |
| `m4-complete` | `57115ec` |
| `m5-complete` | `bf5132f` |

## Commit hashes: original, after the first rewrite, final

Commits made after the first rewrite have no original hash ("–").

| Original | After 2026-11-06 | Final | Date | Subject |
|---|---|---|---|---|
| `711b0dd` | `711b0dd` | `9175abe` | 2026-10-22 | Initial project setup |
| `756deae` | `d3c0d1e` | `e50e96d` | 2026-10-22 | Add project brief and Claude Code instructions |
| `25bfaca` | `9420a8e` | `dec8999` | 2026-10-22 | Rebuild environment on Python 3.12 |
| `f4b70e2` | `7223fe8` | `bf76f5f` | 2026-10-22 | Add project brief and Claude Code instructions |
| `b1f533d` | `ace14db` | `1eab774` | 2026-10-22 | M1: seeded incident simulator and read-only investigation tools |
| `2dbd8aa` | `43dca54` | `71423a1` | 2026-10-22 | M2a: difficulty tiers, dev/held-out split, frozen manifests |
| `d989d99` | `9e48167` | `919a228` | 2026-10-22 | Document held-out keyword brittleness, small dev tier cells and decoy placement |
| `6ef60fc` | `a1f8a78` | `c6dcc63` | 2026-10-22 | Merge branch 'm2a-tiers-split': M2a tiers, dev/held-out split, frozen manifests |
| `58cf555` | `04e4856` | `a43d7cc` | 2026-10-22 | Viewer page 1: local dev-only scenario explorer |
| `38a5e4e` | `c26b723` | `976b6cd` | 2026-10-22 | Merge branch 'viewer-page-1': local dev-only scenario explorer |
| `6f8a312` | `9016748` | `80fac20` | 2026-10-22 | Pre-register rule baseline specification v1 before implementation |
| `015e654` | `b1a5bac` | `0843f56` | 2026-10-22 | M2b: report contract, rule baseline v1, floors, evaluation harness |
| `2fa4e5f` | `e796c8a` | `5186a5b` | 2026-10-22 | M2b: first dev results for rule baseline v1 and floors |
| `894c21c` | `aa2bed4` | `54e7fdb` | 2026-10-22 | Merge branch 'm2b-baseline-eval': report contract, rule baseline v1, floors, evaluation harness, first dev results |
| `e01fb93` | `b1eb289` | `d973eb9` | 2026-10-22 | get_window tool, headline evidence validity, missing-evidence naming score |
| `0c7940d` | `e1f912c` | `8e36b8d` | 2026-10-22 | Pre-register harder-benchmark principles and success criterion before generator v4 |
| `8d3454b` | `e161d0c` | `6eb8035` | 2026-10-22 | Generator v4: overlapping symptoms in the ambiguous tier, gaps to window end |
| `4a8557c` | `f0a3d7d` | `157067a` | 2026-10-22 | Generator v4 dev results for baseline v1 and floors, beside v3 |
| `b4fe73e` | `82b4590` | `5ba6416` | 2026-10-22 | M2 viewer page: tier counts and dev results with floors as reference lines |
| `6d9a943` | `a5804d9` | `172498f` | 2026-10-22 | Merge branch 'm2c-benchmark-v4': get_window, headline evidence validity, generator v4, M2 viewer page |
| `12359f4` | `da33fc9` | `2ad3f0c` | 2026-10-22 | Pre-register injection twins, paired tier ablation and v5 criterion before any generator change |
| `e8c9279` | `da19f3f` | `96ad3df` | 2026-10-22 | Generator v5: independent stream per difficulty mechanism, injection twins, paired metrics, dev ablation |
| `a7359e6` | `479ec89` | `a81c8ce` | 2026-10-22 | Generator v5 dev results and paired ablation for baseline v1 and floors, beside v4; docs |
| `4115fb2` | `5eee9a3` | `c374ca1` | 2026-10-22 | Fix M2 viewer crash on non-investigator result files; ablation panel; real-data render check |
| `d3b3cbd` | `d0bb1ef` | `e63599b` | 2026-10-22 | Docs: mark M2 complete with five findings; README limitations; next action M3 planning |
| `b866e20` | `0e47971` | `925d43a` | 2026-10-22 | Merge branch 'm2d-paired-ablation': generator v5, paired twins and ablation, viewer fix, M2 complete |
| `1bc30cd` | `fae2ae4` | `35499ae` | 2026-10-23 | M3 plan (approved with changes): feasibility pilot design, verified Ollama and pricing facts |
| `d10d1c1` | `cf01490` | `67fa923` | 2026-10-23 | Merge branch 'm3-plan': approved M3 plan |
| `c1f8623` | `15b2237` | `c0c3e39` | 2026-10-23 | Pre-register M3 pilot questions, bounds and decision rule before any M3 code |
| `0293830` | `43086ec` | `1c34ca3` | 2026-10-23 | M3 stage A: LLM adapter, mock and Ollama clients, tool loop, traces, pilot CLI, network guard, M3 viewer page |
| `51245f7` | `1977e29` | `2b176d0` | 2026-10-23 | M3 stage A: mock pilot traces (scripted policy, not a model) for the M3 viewer page |
| `222af9e` | `27f7e4d` | `5e248ea` | 2026-10-23 | Merge branch 'm3-stage-a': M3 stage A (LLM adapter, tool loop, pilot CLI, network guard, M3 viewer page) |
| `e25480b` | `0a58eb9` | `af5a1b8` | 2026-10-23 | Mark M3 stage A complete |
| `1b4043f` | `bca1a03` | `7e9fba0` | 2026-10-23 | M3 stage B: --smoke option, Ollama environment record, thinking-off smoke run on a non-pilot scenario |
| `517df7a` | `3744f08` | `35a6490` | 2026-10-23 | Pilot CLI: plain-text progress on stderr (one line per model turn, one per run), --quiet |
| `908fb39` | `2f74331` | `cf736d7` | 2026-10-23 | PROGRESS: record the progress-display commit |
| `272dc9d` | `a577312` | `aff3326` | 2026-10-23 | PROGRESS: smoke-run observations and thinking-mode decision (off) before the 7 pilot runs |
| `74dec71` | `3be0ad9` | `c9a1d12` | 2026-10-23 | Record M3 pilot attempt 1 (aborted by the swap guard after 3 of 7 runs); keep its files unchanged |
| `3c28b0b` | `e892742` | `75cc569` | 2026-10-23 | Pilot attempt 2 setup: unload the model after every run, attempt directories, abort summary, overflow indicator |
| `2f151cd` | `8d14f1d` | `7feb989` | 2026-10-23 | PROGRESS: attempt 2 configuration and conditions, recorded before the rerun |
| `a232a37` | `406898c` | `f8ebe46` | 2026-10-23 | M3 stage B complete: attempt 2 results (7/7 runs, rule verdict local_feasible with caveats), server-log context extract, M4 carry-forward |
| `8eacfd0` | `bff28bd` | `c8b1e70` | 2026-10-23 | Merge branch 'm3-stage-b': M3 stage B (Ollama pilot: attempt 1 aborted and recorded, attempt 2 completed), M3 complete |
| `18f8733` | `47affa6` | `21d2494` | 2026-10-23 | Mark M3 complete (merged, tagged m3-complete) |
| `855af4d` | `d6fa5f2` | `cf4a537` | 2026-10-23 | Pre-register M4 (D1-D8, state machine, context safeguards, fixed 10-scenario set, investigated (a)-(f), rule, no-tuning rule, limitations) before any M4 code |
| `a58b589` | `1f9f54b` | `870ce88` | 2026-10-23 | M4 stage A design correction: bounded ledger view, metric series summaries, shown-only ledger; frozen parameters from the synthetic worst case |
| `7745302` | `6212dc3` | `9e57b0a` | 2026-10-23 | M4 stage A: explicit-state agent with managed context, metrics, CLI, M4 viewer page (no model, no network) |
| `8def741` | `b863ddb` | `b6fe499` | 2026-10-23 | PROGRESS/CLAUDE: M4 stage A done, awaiting review; notes and deviations |
| `50dbf88` | `7550b69` | `d75e51e` | 2026-10-24 | Pre-register M4 stage B (hardware-abort retry rule, smoke scenario sc-45fa1390ea, revision rule) before any run |
| `796de66` | `951a7c1` | `4787798` | 2026-10-27 | M4 stage B part 1: smoke run outputs (sc-45fa1390ea, original and twin), server-log context and cache extracts |
| `8ea19b0` | `dfdd78a` | `ca12fb8` | 2026-10-27 | PROGRESS: smoke run 1 findings (injection never reached the model; runs not reproducible at temperature 0, diagnosis), revision limit, smoke-2 start checks |
| `26f4813` | `3dbe89f` | `b922c89` | 2026-10-27 | M4 prompt revision 1 (from smoke run 1): reply-only rule and /no_think; STAGE template hashed, with precondition progress lines |
| `ef2bb0b` | `033d294` | `6d0c646` | 2026-10-27 | M4 stage B: smoke run 2 outputs (prompt 39a474eb; sc-45fa1390ea, original and twin), server-log context and cache extracts |
| `c765230` | `d840b46` | `40476a0` | 2026-10-27 | PROGRESS: qwen3:4b core runs not run (5 of 6 start checks failed); rule not applied; scope of the evidence |
| `0105cd1` | `89591c6` | `a397337` | 2026-10-27 | Harness fix: ProgressClient forwards unload, so unload-after-timeout (D3) reaches the model; regression test through the wrapper |
| `6b3a00e` | `a79924e` | `8a11b55` | 2026-10-27 | Context revision 1: estimator base ratio 3.6 -> 3.1 chars/token (metric-heavy prompts); no prompt hash change |
| `f25996c` | `5b22e7e` | `aa63935` | 2026-10-27 | Pre-register the alternative-model smoke (qwen3:4b-instruct-2507-q4_K_M, verified tag and size); record that qwen3:4b is the thinking-2507 variant |
| `31c8f83` | `15e1bef` | `a81740a` | 2026-10-27 | CLAUDE.md: M4 status (stage A approved; stage B smoke results and the alternative-model smoke) |
| `7499e5c` | `71876a0` | `b26d51b` | 2026-10-28 | M4 stage B: alternative-model smoke outputs (qwen3:4b-instruct-2507-q4_K_M, prompt 39a474eb; sc-45fa1390ea, original and twin), server-log context and cache extracts |
| `9203474` | `89cf076` | `e484b35` | 2026-10-28 | PROGRESS: instruct smoke result (2 of 6 checks failed), user deviations, and the pre-registered bounded exception (change B, prompt revision 2, one more smoke run) |
| `705af12` | `482721c` | `23d7cc7` | 2026-10-28 | M4 change B: after the finish_gathering precondition, 3 empty GATHER calls move to HYPOTHESIZE instead of ending the run |
| `d8bfb71` | `3087735` | `d03ba7e` | 2026-10-28 | M4 prompt revision 2 (the last): every model-facing harness text moves into agent/prompt.py and the hash |
| `dd7a30a` | `ccd0628` | `4f46af4` | 2026-10-28 | PROGRESS and CLAUDE.md: change B (23d7cc7) and prompt revision 2 (d03ba7e, hash feaa4477) recorded; one smoke run pending |
| `2caa126` | `d24a734` | `12671a2` | 2026-10-28 | PROGRESS: amendment to change B (identical-calls trigger advances after the precondition), within prompt revision 2; recorded before the code |
| `f9852cf` | `e4e699f` | `ea3be2e` | 2026-10-28 | M4 change B amendment: after the precondition, 3 identical GATHER calls move to HYPOTHESIZE (revision 2 hash replaced) |
| `66dc483` | `6ab7f66` | `2159ca2` | 2026-10-28 | PROGRESS and CLAUDE.md: revision 2 hash d269d28d recorded (ea3be2e); identical-calls trigger included in change B |
| `34e7b82` | `802f5f4` | `d8a417e` | 2026-10-28 | M4 stage B: instruct smoke attempt 2 outputs (prompt d269d28d, code 2159ca2; sc-45fa1390ea, original and twin), server-log context and cache extracts |
| `1851431` | `e77739f` | `8429e39` | 2026-10-28 | PROGRESS: smoke gate fails (attempt 2), paid hosted plan withdrawn, free-provider research and decision (Groq, qwen/qwen3.8-27b), R1 as context revision 2, hosted smoke pre-registered |
| `ebc4dcd` | `0f4c1d2` | `60b6d91` | 2026-10-28 | M4 context revision 2 (R1): the latest accepted ranking is always rendered in the compacted block |
| `7f6fa08` | `1a4577c` | `4e4534c` | 2026-10-28 | Hosted free-tier client: generic OpenAI-compatible httpx client (Groq registered), wired into agent_run --backend groq |
| `6067f7b` | `dc380de` | `f0bad0b` | 2026-10-28 | PROGRESS and CLAUDE.md: R1 (60b6d91) and the Groq client (4e4534c) recorded; hosted smoke is next |
| `ed0c0d6` | `e16ebd7` | `87b0deb` | 2026-10-28 | PROGRESS: hosted-run decisions (daily-limit rerun, rejected-field rule, 30-min bound on active time with rule thresholds on active time, M5 needs a separate plan) |
| `24b85ae` | `b770098` | `344c4ad` | 2026-10-29 | M4 stage B: Groq hosted smoke outputs (qwen/qwen3.8-27b, prompt d269d28d, code 87b0deb; sc-45fa1390ea, original and twin) |
| `481a078` | `ce6de5e` | `c70b3a4` | 2026-10-29 | Hosted client: strip organization IDs (org_...) from provider error messages before they reach traces |
| `4bb8bce` | `5bcd680` | `1b95692` | 2026-10-29 | PROGRESS: Groq smoke result and stop (gate fails, rerun not used), next backend decision (Mistral free tier, local loop-issued fallback) |
| `2ea8fe3` | `5db12af` | `0ac205b` | 2026-10-29 | PROGRESS: pre-registration for the Mistral free tier and context revision 3 (tool list per state), with the user's two additions |
| `50d7a65` | `58a73cc` | `5fc0c2d` | 2026-10-29 | M4 context revision 3: HYPOTHESIZE and REPORT requests carry only their own tool |
| `181d49d` | `43c1167` | `747b340` | 2026-10-29 | M4: 30-minute bound on active time (wall minus provider waits), and a provider-caused stop aborts the batch |
| `e656475` | `a62f4ce` | `cd3f06c` | 2026-10-29 | Hosted client: Mistral free tier registered (agent_run --backend mistral), served-model pin, hosted data guard |
| `31c3a87` | `87f4c57` | `24d520a` | 2026-10-29 | PROGRESS and CLAUDE.md: context revision 3, active-time bound and batch abort, and the Mistral client recorded; console numbers next |
| `6154875` | `76ed7cb` | `a233596` | 2026-10-29 | PROGRESS: Mistral model choice mistral-large-2512 (Large 3), recorded as a deviation made after seeing the console numbers |
| `06c3d09` | `239efba` | `e7fa297` | 2026-10-29 | M4 stage B: Mistral smoke attempt 1 outputs (mistral-large-2512 refused: HTTP 403 tier_not_allowed on all 4 requests) and PROGRESS entry |
| `ee04309` | `80c01ef` | `01b79d3` | 2026-10-29 | Hosted client: 401 and 403 are provider-caused, so the batch aborts at once |
| `f6a1631` | `e353377` | `68c49f2` | 2026-10-29 | Hosted client: content returned as a list of chunks (Mistral reasoning shape) is handled |
| `8ad0147` | `357027e` | `02e041c` | 2026-10-29 | PROGRESS and CLAUDE.md: both client fixes recorded (01b79d3, 68c49f2); mistral-small-2603 smoke is next |
| `ee25c88` | `5d137a7` | `9ae6f52` | 2026-10-29 | M4 stage B: Mistral Small 4 smoke outputs (429 rate_limited on the first request; pair does not count) and PROGRESS entry |
| `ffbde76` | `cc3fa5e` | `2d86184` | 2026-10-29 | M4 stage B: Ministral smoke outputs (context_exhausted at the first VERIFY request; does not count) and PROGRESS entry with the logged exception |
| `6b38171` | `72c0aba` | `ae1607a` | 2026-10-29 | Hosted client (a): on any 429 or 5xx, record every attempt's status and time and the rate-limit headers |
| `d6dae75` | `7fbd7c8` | `3acb3d9` | 2026-10-29 | Hosted client (b): without retry-after, back off 15, 30 and 60 s (60 s for any later retry) |
| `6d5b482` | `26f7830` | `5ab4bad` | 2026-10-29 | Hosted client (c): the pacer reserves the output cap, counting each attempt as size estimate + max_tokens |
| `c445f13` | `bcb26b9` | `6ad17ef` | 2026-10-29 | M4 context revision 4: estimator calibrated per tool list sent, with a two-ratio estimate for an unseen list |
| `b969b0a` | `1e17c8c` | `f1fbe31` | 2026-10-29 | PROGRESS and CLAUDE.md: client changes (a)-(c), context revision 4 (choice, simulation table, residual risk), rerun settings |
| `f7c7224` | `c8a4f30` | `351f6de` | 2026-10-29 | M4 stage B: Ministral smoke attempt 2 outputs (gate passes: valid reports, top-1 correct, no overflow) and PROGRESS entry |
| `48854dc` | `b8fb7a2` | `652a8ee` | 2026-10-29 | Test fix: pin the old-estimator undercount test to Ministral attempt 1's traces |
| `46e8a42` | `8993e4a` | `520badf` | 2026-10-29 | M4 decision rule: on hosted backends the median-time thresholds use active time (wall minus provider waits) |
| `17fe7f5` | `0aadbc2` | `ac1a3a2` | 2026-10-29 | PROGRESS and CLAUDE.md: core runs approved with conditions (opt-out placeholder, held until confirmed), rule on active time, test-fix note, write-up caveats |
| `3d3fdca` | `8f327bc` | `f54d0f2` | 2026-10-29 | M4 stage B: core run outputs, mistral ministral-14b-2512, attempt 1 (12 runs, code ac1a3a2, not dirty) |
| `0a4ed79` | `9af1f49` | `57115ec` | 2026-10-29 | PROGRESS and CLAUDE.md: Mistral core result (works_locally on a hosted 14B), opt-out status, freeze rule, facts from the core traces |
| `c24bfd3` | `93c70cc` | `5bda184` | 2026-10-29 | docs: M5 options memo (v2 prompt exception, held-out backend options, injection exposure) |
| `5a91582` | `9daa58e` | `0333df1` | 2026-10-29 | docs: M5 pre-registration, committed for review before any v2 model call |
| `98f8372` | `1518f7d` | `dad6497` | 2026-10-29 | docs: M5 pre-registration approved with amendments A1-A5 (references 0333df1; original text unchanged) |
| `a2f805d` | `9128497` | `70aabea` | 2026-10-29 | docs: M5 v2 GATHER wording (exact, for review) and the single-pass baseline design |
| `5c9f31e` | `e4d512a` | `1b2550b` | 2026-10-29 | docs: correct the v2 wording's measured lengths (v1 160, v2 681 characters; +521, about +194 tokens) |
| `c9997b1` | `f537431` | `408bcf7` | 2026-10-29 | docs: M5 pre-registration additions B1-B5, recorded before any code |
| `527810c` | `09313c2` | `fb981d5` | 2026-10-29 | Test fix: the revision-4 never-undercounts replay reads the backend from directories without a smoke- prefix |
| `82056f8` | `89ca590` | `236457a` | 2026-10-29 | M5 stage B: v2 prompt wiring (hash 0a788479), dev-gate set and originals-only runs, dev gate report |
| `b9f05bc` | `adfeebd` | `d1cacce` | 2026-10-29 | M5 stage C: single-pass baseline and its no-timeline arm, with a dev-gate runner |
| `87d0c39` | `7e8448c` | `6f2708a` | 2026-10-29 | M5 stage D: fresh-split generator (one-shot; prints count, hash and a yes/no collision check), hosted allowance |
| `390a573` | `4814053` | `6356626` | 2026-10-29 | PROGRESS and CLAUDE.md: M5 stages B-D recorded (hashes, commits, red-suite windows), collision check pending generation |
| `129b672` | `7b826a7` | `026bb59` | 2026-11-02 | M5 dev gate outputs: v1 and v2 agent arms, single-pass full and no-timeline (outputs only) |
| `dedd4e7` | `ac46004` | `1803ba6` | 2026-11-05 | Test fix: the estimator replay reads a pinned list of agent-trace directories |
| `52daa08` | `c1db227` | `1736230` | 2026-11-05 | M5 dev gate report (outputs only): v2 failed G2 and G4 |
| `e96ac9a` | `b0e4922` | `d749d30` | 2026-11-05 | M5: dev gate outcome recorded (v2 failed, v1 only) and deviation D1 (primary: agent v1 vs single-pass full) |
| `df10d46` | `aa57ca8` | `cd2a171` | 2026-11-05 | M5: fresh-split run path with the fixed slices, and the paired injection safety harness |
| `ad4ed47` | `50e8938` | `4571bb7` | 2026-11-05 | M5 fresh split manifest, frozen (generated once; not viewed) |
| `f945fa5` | `d3b57e0` | `81b5c41` | 2026-11-05 | PROGRESS and CLAUDE.md: fresh split generated (60, 574908ad, no collision), headline run path and safety harness recorded |
| `0f53f48` | `1a2bae0` | `92d3ba4` | 2026-11-05 | M5 operational changes O1-O2: safety test in 3 slices with one rerun each; headline batches run by slice |
| `910b0b5` | `7a76256` | `c4fc298` | 2026-11-05 | M5 headline analysis, built before any fresh-split run |
| `cdc6ea2` | `291311f` | `c7cd586` | 2026-11-05 | PROGRESS and CLAUDE.md: fresh-split safety exposure (21 pairs, all exposed, slices 7/7/7) and the headline analysis recorded |
| `a3765d7` | `439b5ca` | `6915e0b` | 2026-11-05 | M5 fresh-split outputs: 18 headline batches (agent v1, single-pass full, no-timeline; slices 1-6) and 3 safety slices |
| `8c19a9d` | `34f59cd` | `d3556b1` | 2026-11-05 | M5 section 7 secondary measures, built before the fresh analysis was run |
| `f9950e2` | `7e10fd5` | `2eaf683` | 2026-11-05 | M5 headline analysis output (run once on the fresh split) and its record in PROGRESS and CLAUDE.md |
| `545860b` | `f66d51a` | `2ac95b2` | 2026-11-05 | E1: exploratory, post hoc replicate-noise control for the safety test (decided after the safety counts) |
| `3c159f7` | `e9351ac` | `5550c05` | 2026-11-05 | E1 test: twins with reports, so the twin-pair restriction and top1_changed are tested at n = 3 |
| `ca05142` | `c1bea45` | `282ca60` | 2026-11-06 | E1 outputs: 3 replicate slices of the safety originals (7 runs each, attempt 1), run by the user |
| `84b54bd` | `175f3b1` | `24d829a` | 2026-11-06 | E1 report (safety --e1-report, offline): 16 with both reports, 3 disagree; on the 16 twin pairs, twin changed 5 |
| `a53c3f6` | `dedf18d` | `de42b35` | 2026-11-06 | PROGRESS and CLAUDE.md: E1 result (exploratory, post hoc, decided after the safety counts) |
| `054f3d3` | `8cf5b7f` | `626bcfe` | 2026-11-06 | docs: M4 + M5 report (draft), numbers from committed outputs |
| `cf6a30b` | `dd97dc4` | `12dba45` | 2026-11-06 | docs: report diagnosis gains the agent's certificate_expiry misses (facts only) |
| `e409a87` | `5570edf` | `6042959` | 2026-11-06 | docs: report gains a future-work note (a replicate of the two primary arms, not run) |
| `ec0ee37` | `3c7d821` | `72a641c` | 2026-11-06 | CLAUDE.md NEXT points to M6; report notes the impossible api-gateway pool-exhaustion pair as a likely symptom confusion (interpretation) |
| `bdb640b` | `f36869c` | `9ae2464` | 2026-11-06 | docs: M6 plan memo (README, demo, publish checklist) |
| – | `5cdf60b` | `a5fd03d` | 2026-11-06 | History rewritten once (2026-11-06): new hash citations and the old-to-new table |
| – | `6346f9d` | `a9b31e4` | 2026-11-07 | Viewer: never list or read fresh-split runs (M4 page showed m5-fresh traces) |
| – | `2b1eb43` | `ef67499` | 2026-11-07 | M5 viewer page: the fresh-split headline as aggregate counts only |
| – | `76a3f38` | `45b1441` | 2026-11-07 | pytest: a slow marker and a fast subset (-m "not slow": 392 tests, about 36 s) |
| – | `55f336b` | `13e6828` | 2026-11-07 | README for readers of the repo: headline result with its scope and caveats, results table, timed five-minute path without a key, architecture diagram, repository map |
| – | `0aa9714` | `e6812fd` | 2026-11-07 | MIT licence |
| – | `3836298` | `bf5132f` | 2026-11-07 | PROGRESS and CLAUDE.md: M4 and M5 complete, M6 in progress (viewer fix, M5 page, fast subset, README, licence) |
| – | `9867753` | `a827328` | 2026-11-07 | Merge branch 'm4-stage-b': M4 (state-machine agent, Mistral core runs) and M5 (single-pass baseline, fresh-split comparison, safety test, E1, report, M5 viewer page), M6 so far |
| – | `2bf236f` | `92f7904` | 2026-11-07 | Viewer: pin every dependency (29), pandas held at 3.0.6 |
| – | `b5fc284` | `1993f4b` | 2026-11-07 | README: results-at-a-glance figure (D1 2x2 and every arm's top-1 with Wilson intervals) |
| – | `f87ac4a` | `5a29bc8` | 2026-11-07 | docs: threat model (trust boundaries, read-only tools, the injection test's scope, key handling) and a summary at the top of the M4 + M5 report |
| – | `ae20fdc` | `3331be7` | 2026-11-07 | docs: 60-90 s demo walkthrough script (dev runs 3 and 12, M5 page); PROGRESS and CLAUDE.md M6 status |
| – | `1b165c9` | `53ecef3` | 2026-11-07 | docs: threat model records the org_ test value as a confirmed fake fixture |
| – | `e61c5e9` | `80be261` | 2026-11-07 | Tooling: ruff 0.17.4 pinned in requirements-dev.txt (rules E9 and F, line length 120); require Python 3.12+ |
| – | `2ae45cd` | `1ad57c8` | 2026-11-07 | Fix the first ruff findings: 5 unused imports, and an annotation naming Exchange before its local import |
| – | `a62db92` | `e50df29` | 2026-11-07 | CI: lint and the fast test subset on Python 3.12, on push to main and on pull requests |
| – | `d035b07` | `e224e0c` | 2026-11-07 | On-demand workflow (workflow_dispatch) and scripts/run_on_demand.py: one dev-profile scenario, the rule baseline and the scripted mock agent, no model |
| – | `b437059` | `625be4c` | 2026-11-09 | Hosted demo entry point for Streamlit Community Cloud (app/cloud_app.py), hosting steps, README sections |
| – | `a5c0d82` | `a66eb74` | 2026-11-09 | README demo: a scripted 34 s recording of the local viewer (dev runs 3 and 12), GIF with a still fallback |
| `baa5edd` | (removed: empty after the first rewrite) | – | 2026-11-06 | (the removal commit) |
