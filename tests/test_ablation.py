from __future__ import annotations

from pathlib import Path

import pytest

from sentinelops.baselines import INVESTIGATORS
from sentinelops.evaluation.ablation import main, paired_counts, run_ablation
from sentinelops.scenario_files import dump_json
from sentinelops.simulator.datasets import (
    TIER_COUNTS,
    build_injection_twins,
    build_manifest,
    build_split,
    content_sha256,
    manifest_path,
    write_split,
)
from sentinelops.simulator.faults import FaultType
from sentinelops.simulator.profiles import Split, Tier

T, W = ("orders", "bad_deployment"), ("auth", "memory_leak")


def test_paired_counts_are_exact() -> None:
    triples = [(T, T, T), (T, W, W), (T, T, W), (T, W, T), (T, W, ("auth", "config_error"))]
    assert paired_counts(triples) == {"n": 5, "unchanged": 2, "both_correct": 1, "both_wrong": 2,
                                      "correct_only_without": 1, "correct_only_with": 1}


@pytest.fixture(scope="module")
def tmp_dev(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, list]:
    root = tmp_path_factory.mktemp("ablation")
    data_root, manifest_dir = root / "dev", root / "manifests"
    scenarios = build_split(Split.DEV)
    write_split(scenarios, data_root, build_injection_twins(Split.DEV, scenarios))
    manifest_dir.mkdir()
    dump_json(manifest_path(Split.DEV, manifest_dir),
              build_manifest(Split.DEV, scenarios, content_sha256(data_root)))
    return data_root, manifest_dir, scenarios


def test_ablation_pairs_each_mechanism_with_its_tier(tmp_dev) -> None:
    data_root, manifest_dir, scenarios = tmp_dev
    result = run_ablation({"alert_service": INVESTIGATORS["alert_service"]}, data_root, manifest_dir)
    per_tier = TIER_COUNTS[Split.DEV]
    ambiguous, missing = (len(FaultType) * per_tier[t] for t in (Tier.AMBIGUOUS, Tier.MISSING_EVIDENCE))
    expected_n = {"injection": sum(t.injection is not None for _, t in scenarios),
                  "overlap": ambiguous, "decoy": ambiguous, "gap": missing}
    for mechanism, n in expected_n.items():
        c = result["ablation"][mechanism]["alert_service"]
        assert c["n"] == n > 0
        assert c["both_correct"] + c["both_wrong"] + c["correct_only_without"] + c["correct_only_with"] == n
        assert c["unchanged"] >= c["both_correct"]
    assert result["split"] == "dev" and result["metadata"]["generator_version"]


def test_ablation_refuses_data_that_differs_from_the_manifest(tmp_path: Path) -> None:
    missing = tmp_path / "nothing"
    assert main(["--data-root", str(missing), "--manifest-dir", str(missing), "--out-dir", str(missing)]) == 2
    assert not missing.exists()


def test_ablation_has_no_split_argument() -> None:
    with pytest.raises(SystemExit):
        main(["--split", "heldout"])
