"""The hosted demo's entry point (app/cloud_app.py) and its dependency file. Offline; generation runs into a
temporary directory."""

from __future__ import annotations

import ast
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from conftest import REPO_ROOT

APP = REPO_ROOT / "app"


def _pins(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip() and not line.strip().startswith("#")]


def test_app_requirements_equal_the_two_root_files() -> None:
    root = _pins(REPO_ROOT / "requirements.txt") + _pins(REPO_ROOT / "requirements-viewer.txt")
    assert Counter(_pins(APP / "requirements.txt")) == Counter(root), (
        "app/requirements.txt must be exactly requirements.txt plus requirements-viewer.txt")


def _imports(path: Path) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


@pytest.mark.parametrize("path", sorted(APP.rglob("*.py")), ids=lambda p: p.name)
def test_the_viewer_has_no_model_client_network_library_or_secrets(path: Path) -> None:
    banned = ("sentinelops.llm", "sentinelops.agent", "sentinelops.simulator", "httpx", "requests", "openai", "urllib")
    assert not [m for m in _imports(path) if m.startswith(banned)], path.name
    assert "secrets" not in {n.attr for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.Attribute)}


@pytest.fixture()
def cloud(monkeypatch: pytest.MonkeyPatch):
    from app.dev_data import ROOT_ENV

    monkeypatch.delenv(ROOT_ENV, raising=False)  # the app sets it; restored after the test
    import importlib.util

    spec = importlib.util.spec_from_file_location("cloud_app_under_test", APP / "cloud_app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # __name__ is not "__main__", so no page runs
    return module


def test_a_failed_generation_raises_a_clear_error(cloud, tmp_path: Path) -> None:
    with pytest.raises(cloud.DevDataUnavailable, match="generation did not run"):
        cloud.prepare_dev_data(tmp_path, python=str(tmp_path / "no-such-python"))
    with pytest.raises(cloud.DevDataUnavailable, match="generation failed"):
        cloud.prepare_dev_data(tmp_path, python="/usr/bin/false")


def test_data_that_does_not_match_the_frozen_manifest_is_refused(cloud, tmp_path: Path) -> None:
    """A stand-in interpreter "generates" an empty split and passes the check to the real Python, which must fail."""
    fake = tmp_path / "python"
    fake.write_text("#!/bin/sh\n"
                    'if [ "$2" = "sentinelops.simulator" ]; then out="$6"; mkdir -p "$out/scenarios" "$out/ground_truth"; '
                    "exit 0; fi\n"
                    f'exec "{sys.executable}" "$@"\n')
    fake.chmod(0o755)
    with pytest.raises(cloud.DevDataUnavailable, match="manifest check failed"):
        cloud.prepare_dev_data(tmp_path, python=str(fake))


def test_the_page_shows_a_message_instead_of_crashing_when_generation_fails(monkeypatch: pytest.MonkeyPatch,
                                                                            tmp_path: Path) -> None:
    testing = pytest.importorskip("streamlit.testing.v1")
    import streamlit as st

    from app.dev_data import ROOT_ENV

    monkeypatch.delenv(ROOT_ENV, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "no-such-python"))
    st.cache_resource.clear()
    at = testing.AppTest.from_file(str(APP / "cloud_app.py"), default_timeout=60)
    at.run()
    st.cache_resource.clear()
    assert not at.exception, [e.value for e in at.exception]
    assert any("could not prepare its synthetic dev data" in e.value for e in at.error)


@pytest.mark.slow
def test_generation_goes_to_a_temporary_directory_and_matches_the_dev_manifest(cloud, tmp_path: Path) -> None:
    before = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True).stdout
    root = cloud.prepare_dev_data(tmp_path)
    assert root.is_relative_to(tmp_path) and root.name == "scenarios" and len(list(root.iterdir())) == 40
    assert (root.parent / "ground_truth").is_dir() and "heldout" not in root.parts
    after = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True).stdout
    assert after == before  # no tracked (or new untracked) file in the repository changed


@pytest.mark.slow
def test_the_running_app_never_imports_the_simulator() -> None:
    """In a fresh interpreter: render the hosted entry point, then check the process's modules."""
    code = (
        "import sys\n"
        "from streamlit.testing.v1 import AppTest\n"
        f"at = AppTest.from_file({str(APP / 'cloud_app.py')!r}, default_timeout=120)\n"
        "at.run()\n"
        "assert not at.exception, [e.value for e in at.exception]\n"
        "assert not at.error, [e.value for e in at.error]\n"
        "print('SIMULATOR', any(m.startswith('sentinelops.simulator') for m in sys.modules))\n"
        "print('LLM', any(m.startswith(('sentinelops.llm', 'httpx')) for m in sys.modules))\n"
    )
    pytest.importorskip("streamlit")
    done = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stderr[-2000:]
    assert "SIMULATOR False" in done.stdout and "LLM False" in done.stdout, done.stdout
