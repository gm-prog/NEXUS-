"""Launch one independently identified Phase 1A service process."""

from __future__ import annotations

import os

import uvicorn

from phase1a_demo.app import create_app


def main() -> None:
    service_name = os.environ.get("NEXUS_SERVICE_NAME", "")
    if not service_name:
        raise SystemExit("NEXUS_SERVICE_NAME must identify one Phase 1A service")
    app = create_app(service_name)
    host = os.environ.get("NEXUS_BIND_HOST", "0.0.0.0")
    port = int(os.environ.get("NEXUS_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
