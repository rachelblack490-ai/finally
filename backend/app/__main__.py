"""Run the FinAlly sidecar: ``python -m app``.

Binds loopback only (``FINALLY_HOST`` / ``FINALLY_PORT``, defaults
127.0.0.1:8000). Never binds 0.0.0.0.
"""

from __future__ import annotations

import uvicorn

from . import config


def main() -> None:
    config.load_dotenv()
    host = config.get_host()
    port = config.get_port()
    uvicorn.run("app.main:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
