"""M5 stage D: the fresh split's frozen constants, its one-shot generator, the yes/no ID-collision check through the
data guard's membership sets, and the hosted allowance. The real fresh split is never built here: generator tests
use a tiny substitute seed and schedule."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinelops.evaluation import m5_fresh
from sentinelops.evaluation.agent_run import Refused, check_hosted_target, collides_with_frozen_splits
from sentinelops.simulator import datasets
from sentinelops.simulator.datasets import SPLIT_SEEDS, TIER_COUNTS
from sentinelops.simulator.profiles import FROZEN_SPLITS, HELDOUT_PROFILE, PROFILES, Split, Tier


def test_the_frozen_constants_are_the_preregistered_ones() -> None:
    assert SPLIT_SEEDS[Split.M5FRESH] == m5_fresh.seed_from_rule() == 447518130
    assert SPLIT_SEEDS[Split.M5FRESH] not in (SPLIT_SEEDS[Split.DEV], SPLIT_SEEDS[Split.HELDOUT])
    profile = PROFILES[Split.M5FRESH]
    assert (profile.variants, profile.trigger_lag_min) == (HELDOUT_PROFILE.variants, HELDOUT_PROFILE.trigger_lag_min)
    assert TIER_COUNTS[Split.M5FRESH] == TIER_COUNTS[Split.HELDOUT]
    assert 5 * sum(TIER_COUNTS[Split.M5FRESH].values()) == 60


def test_generic_clis_and_split_tests_never_handle_the_fresh_split() -> None:
    from sentinelops.evaluation.__main__ import main as evaluate
    from sentinelops.simulator.__main__ import main as simulate

    assert Split.M5FRESH not in FROZEN_SPLITS
    with pytest.raises(SystemExit):
        simulate(["--split", "m5fresh"])
    with pytest.raises(SystemExit):
        evaluate(["--split", "m5fresh"])


def _manifests(root: Path, dev_ids=("sc-00000000aa",), heldout_ids=("sc-00000000bb",)) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for name, ids in (("dev", dev_ids), ("heldout", heldout_ids)):
        (root / f"{name}.json").write_text(json.dumps({"scenario_ids": list(ids)}))
    return root


@pytest.fixture()
def tiny_fresh(monkeypatch: pytest.MonkeyPatch):
    """A substitute fresh split: a different seed and one scenario per cell of one tier (5 scenarios)."""
    monkeypatch.setitem(datasets.SPLIT_SEEDS, Split.M5FRESH, 4242)
    monkeypatch.setitem(datasets.TIER_COUNTS, Split.M5FRESH, {Tier.STANDARD: 1})
    monkeypatch.setattr(m5_fresh, "seed_from_rule", lambda rule=None: 4242)


def test_the_generator_prints_only_count_hash_and_yes_no(tiny_fresh, tmp_path: Path, capsys) -> None:
    manifests = _manifests(tmp_path / "manifests")
    out = tmp_path / "data" / "m5fresh"
    assert m5_fresh.main(["--generate", "--out", str(out), "--manifest-dir", str(manifests)]) == 0
    printed = capsys.readouterr().out
    manifest = json.loads((manifests / "m5fresh.json").read_text())
    assert printed.strip() == (f"m5fresh: 5 scenarios, sha256={manifest['content_sha256']}; "
                               f"ID collision with dev or held-out: no")
    assert "sc-" not in printed and str(out) not in printed  # no IDs, no paths
    assert manifest["split"] == "m5fresh" and manifest["n"] == 5 and manifest["seed"] == 4242
    assert (out / "scenarios").is_dir() and (out / "ground_truth").is_dir()


def test_the_generator_runs_once_and_never_under_heldout(tiny_fresh, tmp_path: Path, capsys) -> None:
    manifests = _manifests(tmp_path / "manifests")
    out = tmp_path / "data" / "m5fresh"
    assert m5_fresh.main(["--generate", "--out", str(out), "--manifest-dir", str(manifests)]) == 0
    assert m5_fresh.main(["--generate", "--out", str(out), "--manifest-dir", str(manifests)]) == 2
    assert "generated once" in capsys.readouterr().err
    other = _manifests(tmp_path / "other")
    assert m5_fresh.main(["--generate", "--out", str(tmp_path / "data" / "heldout" / "x"),
                          "--manifest-dir", str(other)]) == 2
    assert not (other / "m5fresh.json").exists()


def test_the_seed_must_match_its_rule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(datasets.SPLIT_SEEDS, Split.M5FRESH, 1)
    with pytest.raises(m5_fresh.Refused):
        m5_fresh.generate(tmp_path / "out", _manifests(tmp_path / "manifests"))


@pytest.mark.slow
def test_the_collision_check_is_yes_or_no_through_membership(tiny_fresh, tmp_path: Path, capsys) -> None:
    manifests = _manifests(tmp_path / "manifests", dev_ids=("sc-1111111111",), heldout_ids=("sc-2222222222",))
    assert collides_with_frozen_splits(["sc-3333333333"], manifests) is False
    assert collides_with_frozen_splits(["sc-3333333333", "sc-2222222222"], manifests) is True
    # Through the generator: make the substitute split's first ID a "held-out" ID; it must print yes and exit 1.
    probe = datasets.build_split(Split.M5FRESH)[0][0].scenario_id
    colliding = _manifests(tmp_path / "colliding", heldout_ids=(probe,))
    assert m5_fresh.main(["--generate", "--out", str(tmp_path / "c" / "m5fresh"), "--manifest-dir",
                          str(colliding)]) == 1
    printed = capsys.readouterr().out
    assert printed.rstrip().endswith("ID collision with dev or held-out: yes") and probe not in printed


def test_the_hosted_allowance_covers_the_fresh_split_and_never_heldout(tmp_path: Path) -> None:
    manifests = _manifests(tmp_path / "m")
    (manifests / "m5fresh.json").write_text(json.dumps({"scenario_ids": ["sc-4444444444"]}))
    check_hosted_target(tmp_path / "data" / "m5fresh", ["sc-4444444444"], manifests, split=Split.M5FRESH)
    with pytest.raises(Refused, match="not in the m5fresh manifest"):
        check_hosted_target(tmp_path / "data" / "m5fresh", ["sc-00000000aa"], manifests, split=Split.M5FRESH)
    with pytest.raises(Refused, match="held-out"):
        check_hosted_target(tmp_path / "data" / "heldout", ["sc-4444444444"], manifests, split=Split.M5FRESH)
    with pytest.raises(Refused, match="held-out"):
        check_hosted_target(tmp_path / "data" / "x", ["sc-00000000bb"], manifests, split=Split.HELDOUT)
    check_hosted_target(tmp_path / "data" / "dev", ["sc-00000000aa"], manifests)  # the dev default is unchanged
