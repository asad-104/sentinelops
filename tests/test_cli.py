from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from sentinelops.scenario_files import OBSERVABLE_FILES

from conftest import REPO_ROOT


def _run_cli(cwd: Path, hash_seed: str, *extra: str) -> None:
    cwd.mkdir(parents=True)
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT), "PYTHONHASHSEED": hash_seed}
    subprocess.run([sys.executable, "-m", "sentinelops.simulator", "--seed", "1", "--n", "5", *extra],
                   cwd=cwd, env=env, check=True, capture_output=True)


def _snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_cli_writes_observable_and_ground_truth_separately(tmp_path: Path) -> None:
    _run_cli(tmp_path / "run", "0")
    data = tmp_path / "run" / "data"
    scenario_dirs = sorted((data / "scenarios").iterdir())
    truth_files = sorted((data / "ground_truth").iterdir())
    assert len(scenario_dirs) == len(truth_files) == 5
    for scenario_dir in scenario_dirs:
        assert sorted(p.name for p in scenario_dir.iterdir()) == sorted(OBSERVABLE_FILES)
        truth = json.loads((data / "ground_truth" / f"{scenario_dir.name}.json").read_text())
        assert truth["scenario_id"] == scenario_dir.name


def test_cli_output_is_byte_identical(tmp_path: Path) -> None:
    """Same seed, different hash seeds and directories: identical bytes."""
    _run_cli(tmp_path / "a", "0")
    _run_cli(tmp_path / "b", "12345")
    first, second = _snapshot(tmp_path / "a"), _snapshot(tmp_path / "b")
    assert first.keys() == second.keys() and len(first) == 5 * (len(OBSERVABLE_FILES) + 1)
    differing = [name for name in first if first[name] != second[name]]
    assert not differing


def test_cli_rejects_bad_n(tmp_path: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    result = subprocess.run([sys.executable, "-m", "sentinelops.simulator", "--seed", "1", "--n", "0"],
                            cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode != 0 and "--n" in result.stderr
