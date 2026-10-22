"""CLI for generating scenarios.

  python -m sentinelops.simulator --seed 1 --n 5          ad-hoc standard scenarios in data/
  python -m sentinelops.simulator --split dev [--freeze]  frozen split in data/dev/

``--freeze`` rewrites ``eval/manifests/<split>.json``. For the held-out split,
output is limited to the scenario count and content hash.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from sentinelops.scenario_files import dump_json, write_observable
from sentinelops.simulator.datasets import (
    DEFAULT_MANIFEST_DIR,
    TWINS_DIR,
    build_injection_twins,
    build_manifest,
    build_split,
    content_sha256,
    load_manifest,
    manifest_path,
    write_split,
)
from sentinelops.simulator.generator import generate_dataset
from sentinelops.simulator.profiles import Split


def _adhoc(seed: int, n: int, out: Path) -> None:
    ground_truth_dir = out / "ground_truth"
    ground_truth_dir.mkdir(parents=True, exist_ok=True)
    for observable, truth in generate_dataset(seed, n):
        write_observable(observable, out / "scenarios" / observable.scenario_id)
        dump_json(ground_truth_dir / f"{truth.scenario_id}.json", truth.model_dump(mode="json"))
        print(f"{observable.scenario_id}  logs={len(observable.logs)}  alert={observable.alert.service}")
    print(f"wrote {n} scenarios to {out / 'scenarios'} and ground truth to {ground_truth_dir}")


def _split(split: Split, out: Path, manifest_dir: Path, freeze: bool) -> None:
    scenarios = build_split(split)
    twins = build_injection_twins(split, scenarios)
    # Start clean so stale files from older generator versions cannot change the hash.
    # Only the subdirectories this command owns are removed.
    for owned in ("scenarios", "ground_truth", TWINS_DIR):
        shutil.rmtree(out / owned, ignore_errors=True)
    write_split(scenarios, out, twins)
    sha256 = content_sha256(out)
    frozen = load_manifest(split, manifest_dir)
    if freeze:
        manifest_dir.mkdir(parents=True, exist_ok=True)
        dump_json(manifest_path(split, manifest_dir), build_manifest(split, scenarios, sha256))
    status = "frozen" if freeze else (
        "no manifest" if frozen is None else
        "matches manifest" if frozen["content_sha256"] == sha256 else "DIFFERS from manifest")
    # Held-out: count and hash only. Never IDs, paths or contents.
    print(f"{split.value}: {len(scenarios)} scenarios, sha256={sha256} ({status})")
    if split is Split.DEV:
        print(f"wrote {out} ({len(twins)} injection twins)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sentinelops.simulator", description="Generate scenarios.")
    parser.add_argument("--split", type=Split, choices=list(Split), help="generate a frozen split")
    parser.add_argument("--freeze", action="store_true", help="rewrite the split's manifest")
    parser.add_argument("--seed", type=int, help="dataset seed (ad-hoc mode)")
    parser.add_argument("--n", type=int, help="number of scenarios, 1-10000 (ad-hoc mode)")
    parser.add_argument("--out", type=Path, help="output root (default: data, or data/<split>)")
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.split is not None:
        if args.seed is not None or args.n is not None:
            parser.error("--split cannot be combined with --seed/--n")
        _split(args.split, args.out or Path("data") / args.split.value, args.manifest_dir, args.freeze)
        return 0
    if args.freeze:
        parser.error("--freeze requires --split")
    if args.seed is None or args.n is None:
        parser.error("either --split or both --seed and --n are required")
    if not 1 <= args.n <= 10_000:
        parser.error("--n must be between 1 and 10000")
    _adhoc(args.seed, args.n, args.out or Path("data"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
