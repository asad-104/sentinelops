"""M5 fresh split, generated once: ``python -m sentinelops.evaluation.m5_fresh --generate``.

Pre-registered 2026-10-29 (docs/m5_preregistration.md section 4, amendment A4). Generator v5 unchanged; held-out's
profile and tier counts (60 scenarios) and injection twins; the seed fixed by rule (``M5FRESH_SEED_RULE``). It
refuses to run if the split or its manifest already exists, and never writes under a held-out path. Output is
limited to the scenario count, the content hash and a yes/no ID-collision result against the dev and held-out
manifests (the data guard's membership check); no IDs, paths or contents are printed. The real held-out split is
not read, generated or touched.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from sentinelops.evaluation.agent_run import collides_with_frozen_splits
from sentinelops.scenario_files import dump_json
from sentinelops.simulator.datasets import (
    DEFAULT_MANIFEST_DIR,
    M5FRESH_SEED_RULE,
    SPLIT_SEEDS,
    build_injection_twins,
    build_manifest,
    build_split,
    content_sha256,
    manifest_path,
    write_split,
)
from sentinelops.simulator.profiles import Split

DEFAULT_OUT = Path("data") / Split.M5FRESH.value


class Refused(Exception):
    pass


def seed_from_rule(rule: str = M5FRESH_SEED_RULE) -> int:
    return int.from_bytes(hashlib.sha256(rule.encode()).digest()[:4], "big")


def generate(out: Path = DEFAULT_OUT, manifest_dir: Path = DEFAULT_MANIFEST_DIR) -> dict[str, object]:
    if SPLIT_SEEDS[Split.M5FRESH] != seed_from_rule():
        raise Refused("the fresh split's seed does not match its pre-registered rule")
    if Split.HELDOUT.value in out.resolve().parts:
        raise Refused("the fresh split is never written under a held-out path")
    if manifest_path(Split.M5FRESH, manifest_dir).exists() or (out.exists() and any(out.iterdir())):
        raise Refused("the fresh split is generated once; its manifest or data already exists")
    scenarios = build_split(Split.M5FRESH)
    twins = build_injection_twins(Split.M5FRESH, scenarios)
    write_split(scenarios, out, twins)
    sha256 = content_sha256(out)
    dump_json(manifest_path(Split.M5FRESH, manifest_dir), build_manifest(Split.M5FRESH, scenarios, sha256))
    collision = collides_with_frozen_splits([o.scenario_id for o, _ in scenarios], manifest_dir)
    return {"n": len(scenarios), "sha256": sha256, "collision": collision}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sentinelops.evaluation.m5_fresh")
    parser.add_argument("--generate", action="store_true", required=True, help="generate the fresh split (once)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=argparse.SUPPRESS)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        result = generate(args.out, args.manifest_dir)
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    # Count, hash and yes/no only. Never IDs, paths or contents.
    print(f"m5fresh: {result['n']} scenarios, sha256={result['sha256']}; "
          f"ID collision with dev or held-out: {'yes' if result['collision'] else 'no'}")
    return 0 if not result["collision"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
