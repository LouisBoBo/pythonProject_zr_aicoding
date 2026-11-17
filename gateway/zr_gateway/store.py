"""SQLite-backed sessions and the usage log. Accounts live in MES; the gateway never stores passwords."""

from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  token_digest TEXT PRIMARY KEY,
  username     TEXT NOT NULL,
  enterprise   TEXT NOT NULL,
  expires_at   INTEGER NOT NULL,
  created_at   INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(username);

CREATE TABLE IF NOT EXISTS usage_records (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id    TEXT NOT NULL UNIQUE,
  username      TEXT NOT NULL,
  enterprise    TEXT NOT NULL,
  model_alias   TEXT NOT NULL,
  real_name     TEXT NOT NULL,
  provider_id   TEXT NOT NULL DEFAULT '',
  key_hint      TEXT NOT NULL DEFAULT '',
  purpose       TEXT NOT NULL DEFAULT 'llm',
  input_tokens  INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  status        TEXT NOT NULL DEFAULT 'ok',
  latency_ms    INTEGER NOT NULL DEFAULT 0,
  created_at    INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_usage_user_time ON usage_records(username, created_at);
CREATE INDEX IF NOT EXISTS idx_usage_time ON usage_records(created_at);
"""

# Columns added after the first deployment; older databases get them via ALTER TABLE.
USAGE_COLUMNS = (
    ("provider_id", "TEXT NOT NULL DEFAULT ''"),
    ("key_hint", "TEXT NOT NULL DEFAULT ''"),
    ("purpose", "TEXT NOT NULL DEFAULT 'llm'"),
)

DEFAULT_USAGE_WINDOW_SECONDS = 30 * 24 * 60 * 60


@dataclass(frozen=True)
class Session:
    """An authenticated request context; the token itself was never stored."""

    username: str
    enterprise: str
    expires_at: int


class Store:
    """Opens one short-lived connection per call so no lock survives an exception."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(SCHEMA)
            self._migrate(connection)
            connection.commit()

    def _migrate(self, connection: sqlite3.Connection) -> None:
        """Adds columns introduced after the first deployment; safe to run on every start."""
        existing = {row["name"] for row in connection.execute("PRAGMA table_info(usage_records)")}
        for name, ddl in USAGE_COLUMNS:
            if name not in existing:
                connection.execute(f"ALTER TABLE usage_records ADD COLUMN {name} {ddl}")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        return connection

    def create_session(
        self,
        token_digest: str,
        username: str,
        enterprise: str,
        expires_at: int,
        now: int | None = None,
    ) -> None:
        stamp = int(time.time()) if now is None else now
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (stamp,))
            connection.execute(
                "INSERT INTO sessions (token_digest, username, enterprise, expires_at, created_at) VALUES (?, ?, ?, ?, ?)",
                (token_digest, username, enterprise, expires_at, stamp),
            )

    def resolve_session(self, token_digest: str, now: int | None = None) -> Session | None:
        """@returns the live session for `token_digest`, or None when expired or missing."""
        stamp = int(time.time()) if now is None else now
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT username, enterprise, expires_at FROM sessions WHERE token_digest = ? AND expires_at > ?",
                (token_digest, stamp),
            ).fetchone()
        if row is None:
            return None
        return Session(
            username=row["username"],
            enterprise=row["enterprise"],
            expires_at=row["expires_at"],
        )

    def revoke_sessions(self, username: str) -> int:
        """@returns how many sessions were dropped for `username`."""
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute("DELETE FROM sessions WHERE username = ?", (username,))
            return int(cursor.rowcount)

    def record_usage(
        self,
        *,
        request_id: str,
        session: Session,
        model_alias: str,
        real_name: str,
        input_tokens: int,
        output_tokens: int,
        status: str,
        latency_ms: int,
        provider_id: str = "",
        key_hint: str = "",
        purpose: str = "llm",
        now: int | None = None,
    ) -> None:
        stamp = int(time.time()) if now is None else now
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO usage_records
                  (request_id, username, enterprise, model_alias, real_name, provider_id, key_hint, purpose,
                   input_tokens, output_tokens, status, latency_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    session.username,
                    session.enterprise,
                    model_alias,
                    real_name,
                    provider_id,
                    key_hint,
                    purpose,
                    max(0, input_tokens),
                    max(0, output_tokens),
                    status,
                    max(0, latency_ms),
                    stamp,
                ),
            )

    def aggregate_models(
        self,
        *,
        start: int,
        end: int,
        enterprise: str = "",
        username: str = "",
    ) -> list[dict]:
        """@returns per provider/key/model totals in `[start, end)`; never includes the key itself."""
        filters = ["created_at >= ?", "created_at < ?"]
        parameters: list[object] = [int(start), int(end)]
        if enterprise != "":
            filters.append("enterprise = ?")
            parameters.append(enterprise)
        if username != "":
            filters.append("username = ?")
            parameters.append(username)
        query = f"""
            SELECT provider_id, key_hint, model_alias, real_name, purpose,
                   COUNT(*) AS calls,
                   COALESCE(SUM(input_tokens), 0) AS input_tokens,
                   COALESCE(SUM(output_tokens), 0) AS output_tokens,
                   MAX(created_at) AS last_at
            FROM usage_records
            WHERE {' AND '.join(filters)}
            GROUP BY provider_id, key_hint, model_alias, real_name, purpose
            ORDER BY calls DESC, model_alias ASC, provider_id ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [
            {
                "provider": row["provider_id"],
                "keyHint": row["key_hint"],
                "alias": row["model_alias"],
                "model": row["real_name"],
                "purpose": row["purpose"],
                "calls": int(row["calls"]),
                "inputTokens": int(row["input_tokens"]),
                "outputTokens": int(row["output_tokens"]),
                "lastAt": int(row["last_at"]),
            }
            for row in rows
        ]
