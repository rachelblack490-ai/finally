"""Tests for the desktop launcher's headless helpers (no GUI import)."""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

# The desktop launcher lives outside the backend package.
DESKTOP_DIR = Path(__file__).resolve().parents[3] / "desktop"
sys.path.insert(0, str(DESKTOP_DIR))

import launcher  # noqa: E402


def test_find_free_port_returns_preferred_when_free():
    # Find something almost certainly free by probing a high base.
    port = launcher.find_free_port(53123, span=5)
    assert 53123 <= port <= 53127


def test_find_free_port_skips_taken_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as taken:
        taken.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        taken.bind(("127.0.0.1", 53200))
        taken.listen(1)
        port = launcher.find_free_port(53200, span=5)
        assert port != 53200
        assert 53201 <= port <= 53204


def test_find_free_port_raises_when_none_free():
    socks = []
    try:
        for p in range(53300, 53303):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", p))
            s.listen(1)
            socks.append(s)
        with pytest.raises(RuntimeError):
            launcher.find_free_port(53300, span=3)
    finally:
        for s in socks:
            s.close()


def test_wait_for_health_times_out_quickly():
    # Nothing is listening here; should give up fast.
    assert launcher.wait_for_health("http://127.0.0.1:53999/nope", timeout=0.5) is False
