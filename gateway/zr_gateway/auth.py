"""Opaque bearer tokens for gateway sessions. Only digests are stored."""

from __future__ import annotations

import base64
import hashlib
import re
import secrets

MAX_CREDENTIAL_LENGTH = 256
ENTERPRISE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def new_token() -> str:
    """@returns an opaque 256-bit token, URL-safe and printable."""
    return _encode(secrets.token_bytes(32))


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_enterprise(raw: str) -> str:
    """@returns the stored enterprise key; an empty value becomes `default`."""
    key = raw.strip().lower()
    if key == "":
        return "default"
    if not ENTERPRISE_PATTERN.match(key):
        raise ValueError("enterprise must use a-z, 0-9, _ or -")
    return key
