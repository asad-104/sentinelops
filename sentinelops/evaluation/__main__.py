"""CLI: ``python -m sentinelops.evaluation --split dev --investigator all``.

The held-out split is refused unless ``--final`` is given; final runs are
appended to ``eval/heldout_runs.jsonl``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sentinelops.baselines import INVESTIGATORS
from sentinelops.evaluation.harness import DataMismatch, HeldOutLocked, run_split
from sentinelops.evaluation.metrics import scores_as_dicts, summarize
from sentinelops.evaluation.tables import full_report
from sentinelops.scenario_files import dump_json
from sentinelops.simulator.datasets import DEFAULT_MANIFEST_DIR
from sentinelops.simulator.generator import GENERATOR_VERSION
from sentinelops.simulator.profiles import Split

DEFAULT_RESULTS_ROOT = Path("eval/results")
HELDOUT_RUN_LOG = Path("eval/heldout_runs.jsonl")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sentinelops.evaluation", description="Evaluate investigators.")
    parser.add_argument("--split", type=Split, choices=list(Split), required=True)
    parser.add_argument("--investigator", choices=[*INVESTIGATORS, "all"], default="all")
    parser.add_argument("--final", action="store_true", help="required for the held-out split (milestones only)")
    parser.add_argument("--data-root", type=Path, help="default: data/<split>")
    parser.add_argument("--out-dir", type=Path, help="default: eval/results/generator-v<version>")
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.split is Split.HELDOUT and not args.final:
        print("refused: the held-out split runs only with --final, at milestones", file=sys.stderr)
        return 2

    names = list(INVESTIGATORS) if args.investigator == "all" else [args.investigator]
    data_root = args.data_root or Path("data") / args.split.value
    args.out_dir = args.out_dir or DEFAULT_RESULTS_ROOT / f"generator-v{GENERATOR_VERSION}"
    summaries, metadata = {}, {}
    try:
        for name in names:
            result = run_split(INVESTIGATORS[name], args.split, data_root, final=args.final,
                               manifest_dir=args.manifest_dir)
            summaries[name], metadata = summarize(result.scores), result.metadata
            args.out_dir.mkdir(parents=True, exist_ok=True)
            dump_json(args.out_dir / f"{args.split.value}-{name}.json",
                      {"investigator": name, "split": args.split.value, "metadata": result.metadata,
                       "summary": summaries[name], "scenarios": scores_as_dicts(result.scores)})
    except (HeldOutLocked, DataMismatch) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2

    report = full_report(summaries, args.split.value, metadata)
    if args.investigator == "all":
        (args.out_dir / f"{args.split.value}-summary.md").write_text(report, encoding="utf-8", newline="\n")
    if args.final:
        HELDOUT_RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
        with HELDOUT_RUN_LOG.open("a", encoding="utf-8") as log:
            log.write(json.dumps({"split": args.split.value, "metadata": metadata, "summaries": summaries},
                                 sort_keys=True) + "\n")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
