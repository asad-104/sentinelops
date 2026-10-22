"""The test suite is offline: any network connection attempt fails loudly (see conftest.py)."""

from __future__ import annotations

import socket

import httpx
import pytest

from conftest import NetworkBlocked
from sentinelops.llm.client import ChatMessage
from sentinelops.llm.ollama import OllamaClient


def test_http_requests_are_blocked() -> None:
    with pytest.raises(NetworkBlocked):
        httpx.get("http://127.0.0.1:1")


def test_raw_sockets_are_blocked() -> None:
    with pytest.raises(NetworkBlocked):
        socket.create_connection(("example.com", 80))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s, pytest.raises(NetworkBlocked):
        s.connect(("127.0.0.1", 11434))


def test_a_real_ollama_client_cannot_reach_a_server_in_tests() -> None:
    """Without a mock transport the client would open a socket; the guard stops it."""
    with pytest.raises(NetworkBlocked):
        OllamaClient("qwen3:4b").chat([ChatMessage("user", "hi")], [])
