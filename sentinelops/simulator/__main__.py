"""CLI: ``python -m sentinelops.simulator --seed 1 --n 5``.

Writes observable files to ``<out>/scenarios/<id>/`` and ground truth to
``<out>/ground_truth/<id>.json``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sentinelops.scenario_files import dump_json, write_observable
from sentinelops.simulator.generator import generate_dataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sentinelops.simulator", description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, required=True, help="dataset seed")
    parser.add_argument("--n", type=int, required=True, help="number of scenarios (1-10000)")
    parser.add_argument("--out", type=Path, default=Path("data"), help="output root (default: data)")
    args = parser.parse_args(argv)
    if not 1 <= args.n <= 10_000:
        parser.error("--n must be between 1 and 10000")

    ground_truth_dir = args.out / "ground_truth"
    ground_truth_dir.mkdir(parents=True, exist_ok=True)
    for observable, truth in generate_dataset(args.seed, args.n):
        write_observable(observable, args.out / "scenarios" / observable.scenario_id)
        dump_json(ground_truth_dir / f"{truth.scenario_id}.json", truth.model_dump(mode="json"))
        print(f"{observable.scenario_id}  logs={len(observable.logs)}  alert={observable.alert.service}")
    print(f"wrote {args.n} scenarios to {args.out / 'scenarios'} and ground truth to {ground_truth_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
