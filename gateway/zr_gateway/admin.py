"""Revoke gateway sessions: `python -m zr_gateway.admin revoke NAME`. Accounts live in MES."""

from __future__ import annotations

import argparse

from .config import database_path
from .store import Store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zr-gateway-admin", description="Drop the gateway sessions of one MES account.")
    commands = parser.add_subparsers(dest="command", required=True)
    revoke = commands.add_parser("revoke", help="drop every session of an account")
    revoke.add_argument("name", help="MES username")
    args = parser.parse_args(argv)

    username = args.name.strip()
    count = Store(database_path()).revoke_sessions(username)
    print(f"revoked {count} session(s) for {username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
