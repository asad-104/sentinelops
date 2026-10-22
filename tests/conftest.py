from __future__ import annotations

import socket
from pathlib import Path

import pytest


class NetworkBlocked(RuntimeError):
    """Raised when a test opens a network connection. Not an OSError, so HTTP clients cannot
    turn it into an ordinary connection error and hide the attempt."""


def _install_network_guard() -> None:
    """Tests run offline: any TCP/UDP connect fails loudly. Unix-domain sockets (local IPC) are allowed."""
    real_connect, real_connect_ex = socket.socket.connect, socket.socket.connect_ex

    def guarded(real):
        def connect(self, address, *args, **kwargs):
            if self.family == getattr(socket, "AF_UNIX", object()):
                return real(self, address, *args, **kwargs)
            raise NetworkBlocked(f"network access is disabled in tests (attempted {address!r})")
        return connect

    def create_connection(address, *args, **kwargs):
        raise NetworkBlocked(f"network access is disabled in tests (attempted {address!r})")

    socket.socket.connect = guarded(real_connect)
    socket.socket.connect_ex = guarded(real_connect_ex)
    socket.create_connection = create_connection


_install_network_guard()

from sentinelops.scenario_files import write_observable
from sentinelops.simulator import Scenario, generate_dataset
from sentinelops.tools import ToolSet

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def small_dataset() -> list[Scenario]:
    return generate_dataset(seed=1, n=8)


@pytest.fixture(scope="session")
def large_dataset() -> list[Scenario]:
    """Enough scenarios (40 per fault type) for distribution and leakage checks."""
    return generate_dataset(seed=7, n=200)


@pytest.fixture(scope="session")
def scenarios_root(tmp_path_factory: pytest.TempPathFactory, small_dataset: list[Scenario]) -> Path:
    root = tmp_path_factory.mktemp("scenarios")
    for observable, _ in small_dataset:
        write_observable(observable, root / observable.scenario_id)
    return root


@pytest.fixture()
def toolset(scenarios_root: Path, small_dataset: list[Scenario]) -> ToolSet:
    return ToolSet.from_directory(scenarios_root, small_dataset[0].observable.scenario_id)
