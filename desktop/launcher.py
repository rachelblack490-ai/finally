"""Sidecar lifecycle helpers for the FinAlly desktop shell.

Kept free of any GUI import so the port-selection and health-wait logic can be
unit-tested headlessly.
"""

from __future__ import annotations

import socket
import time
import urllib.request


def find_free_port(preferred: int = 8000, span: int = 11, host: str = "127.0.0.1") -> int:
    """Return the first bindable loopback port from ``preferred`` upward.

    Tries preferred, preferred+1, ... up to ``preferred + span - 1`` (default
    8000–8010). Raises RuntimeError if none are free.
    """
    for port in range(preferred, preferred + span):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port in {preferred}-{preferred + span - 1}")


def wait_for_health(url: str, timeout: float = 30.0, interval: float = 0.25) -> bool:
    """Poll ``url`` until it returns HTTP 200 or ``timeout`` elapses."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:  # noqa: S310 (loopback only)
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(interval)
    return False
