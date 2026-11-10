"""Entry point: `python -m zr_gateway`."""

from __future__ import annotations

import logging
import os

import uvicorn

from .app import create_app
from .config import ConfigError, load_settings


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("ZR_GATEWAY_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        settings = load_settings()
    except ConfigError as error:
        raise SystemExit(f"zr-gateway: {error}")
    try:
        port = int(os.environ.get("ZR_GATEWAY_PORT", "8787"))
    except ValueError:
        raise SystemExit("zr-gateway: ZR_GATEWAY_PORT must be an integer")
    uvicorn.run(
        create_app(settings),
        host=os.environ.get("ZR_GATEWAY_HOST", "127.0.0.1"),
        port=port,
        log_level=os.environ.get("ZR_GATEWAY_LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
