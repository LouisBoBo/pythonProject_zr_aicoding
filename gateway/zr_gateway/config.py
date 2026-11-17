"""Gateway settings read from the environment. No key is ever written to disk or the database."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_UPSTREAM_BASE_URL = "https://api.deepseek.com"
DEFAULT_MES_BASE_URL = "http://127.0.0.1:8009"
DEFAULT_MODEL_MAP = "standard=deepseek-chat,deep=deepseek-reasoner"
DEFAULT_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_UPSTREAM_TIMEOUT_SECONDS = 600.0
DEFAULT_MES_TIMEOUT_SECONDS = 10.0
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
DEFAULT_PROVIDER_ID = "deepseek-official"
DEFAULT_PROVIDER_NAME = "DeepSeek 官方"
LEGACY_MODEL_LABELS = {"standard": "标准", "deep": "深度"}
PURPOSES = frozenset({"llm", "code"})
MIN_ADMIN_TOKEN_LENGTH = 16
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,127}$")


class ConfigError(RuntimeError):
    """Raised when the process cannot start from the current environment."""


@dataclass(frozen=True)
class Provider:
    """One upstream account: where requests go and the key they carry."""

    id: str
    display_name: str
    base_url: str
    key: str

    @property
    def key_hint(self) -> str:
        """Masked form for display; the full key never leaves the server."""
        return mask_key(self.key)


@dataclass(frozen=True)
class ModelRoute:
    """One alias a client may select, bound to exactly one provider and real model."""

    alias: str
    display_name: str
    provider_id: str
    real_name: str
    purpose: str = "llm"


def mask_key(key: str) -> str:
    """Display form: first 8 and last 4 characters, never the secret. Empty when too short."""
    text = (key or "").strip()
    if len(text) < 16:
        return ""
    return f"{text[:8]}*****{text[-4:]}"


@dataclass(frozen=True)
class Settings:
    """Everything the app needs; provider keys are the only secrets."""

    upstream_base_url: str
    upstream_key: str
    model_map: dict[str, str]
    db_path: str
    token_ttl_seconds: int
    upstream_timeout_seconds: float
    mes_base_url: str
    mes_timeout_seconds: float
    force_include_usage: bool
    providers: tuple[Provider, ...] = ()
    models: tuple[ModelRoute, ...] = ()
    admin_token: str = ""

    @property
    def routes(self) -> tuple[ModelRoute, ...]:
        """Alias table the chat route consults; a catalog replaces the legacy map."""
        if self.models:
            return self.models
        return tuple(
            ModelRoute(
                alias=alias,
                display_name=LEGACY_MODEL_LABELS.get(alias, alias),
                provider_id=DEFAULT_PROVIDER_ID,
                real_name=real,
            )
            for alias, real in self.model_map.items()
        )

    def route(self, alias: str) -> ModelRoute | None:
        """@returns the route for `alias`, or None when it is not offered."""
        for item in self.routes:
            if item.alias == alias:
                return item
        return None

    def provider(self, provider_id: str) -> Provider | None:
        """@returns the provider named by a route, or the legacy single provider."""
        for item in self.providers:
            if item.id == provider_id:
                return item
        if self.providers:
            return None
        return Provider(
            id=DEFAULT_PROVIDER_ID,
            display_name=DEFAULT_PROVIDER_NAME,
            base_url=self.upstream_base_url,
            key=self.upstream_key,
        )


def parse_model_map(raw: str) -> dict[str, str]:
    """@returns alias -> upstream model name; @raises ConfigError on a malformed entry."""
    models: dict[str, str] = {}
    for item in raw.split(","):
        item = item.strip()
        if item == "":
            continue
        alias, separator, real_name = item.partition("=")
        alias, real_name = alias.strip(), real_name.strip()
        if separator == "" or alias == "" or real_name == "":
            raise ConfigError(f"model map entry {item!r} must look like alias=real-model-name")
        if alias in models:
            raise ConfigError(f"model map repeats alias {alias!r}")
        models[alias] = real_name
    if not models:
        raise ConfigError("model map has no alias")
    return models


def parse_upstream_base_url(raw: str) -> str:
    """Upstreams may carry a path (for example `/v1`) but no credentials, query, or fragment."""
    try:
        url = urlsplit(raw.strip())
    except ValueError as error:
        raise ConfigError(f"upstream base URL {raw!r} is not a URL") from error
    if url.scheme not in ("https", "http"):
        raise ConfigError("upstream base URL must use https (http is allowed only on loopback)")
    if url.username is not None or url.password is not None:
        raise ConfigError("upstream base URL must not embed credentials")
    if url.query or url.fragment:
        raise ConfigError("upstream base URL must not carry a query or fragment")
    if url.hostname is None:
        raise ConfigError("upstream base URL must include a host")
    if url.scheme == "http" and url.hostname not in LOOPBACK_HOSTS:
        raise ConfigError("plain http is allowed only for a loopback upstream; put the gateway behind TLS otherwise")
    return raw.strip().rstrip("/")


def _read_key(env: Mapping[str, str]) -> str:
    inline = env.get("ZR_GATEWAY_UPSTREAM_KEY", "").strip()
    key_file = env.get("ZR_GATEWAY_UPSTREAM_KEY_FILE", "").strip()
    if inline != "" and key_file != "":
        raise ConfigError("set either ZR_GATEWAY_UPSTREAM_KEY or ZR_GATEWAY_UPSTREAM_KEY_FILE, not both")
    if key_file != "":
        try:
            with open(key_file, "r", encoding="utf-8") as handle:
                inline = handle.read().strip()
        except OSError as error:
            raise ConfigError(f"cannot read ZR_GATEWAY_UPSTREAM_KEY_FILE: {error}") from error
    if inline == "":
        raise ConfigError("ZR_GATEWAY_UPSTREAM_KEY (or ZR_GATEWAY_UPSTREAM_KEY_FILE) is required")
    return inline


def _text(entry: Mapping[str, object], name: str, where: str, fallback: str = "") -> str:
    value = entry.get(name)
    if value is None:
        return fallback
    if not isinstance(value, str):
        raise ConfigError(f"{where}.{name} must be a string")
    text = value.strip()
    return text if text != "" else fallback


def _identifier(value: str, where: str) -> str:
    if _IDENTIFIER.match(value) is None:
        raise ConfigError(f"{where} must match {_IDENTIFIER.pattern}")
    return value


def _provider_key(entry: Mapping[str, object], env: Mapping[str, str], provider_id: str) -> str:
    """Keys come from the environment or a 600 file, never from the catalog itself."""
    where = f"provider {provider_id!r}"
    key_env = _text(entry, "keyEnv", where)
    key_file = _text(entry, "keyFile", where)
    if key_env != "" and key_file != "":
        raise ConfigError(f"{where} must set either keyEnv or keyFile, not both")
    if key_env != "":
        key = env.get(key_env, "").strip()
        if key == "":
            raise ConfigError(f"{where} needs {key_env} in the environment")
    elif key_file != "":
        try:
            with open(key_file, "r", encoding="utf-8") as handle:
                key = handle.read().strip()
        except OSError as error:
            raise ConfigError(f"{where} cannot read keyFile: {error}") from error
        if key == "":
            raise ConfigError(f"{where} keyFile is empty")
    else:
        raise ConfigError(f"{where} must set keyEnv or keyFile")
    if mask_key(key) == "":
        raise ConfigError(f"{where} key is too short to display safely")
    return key


def parse_catalog(document: object, env: Mapping[str, str]) -> tuple[tuple[Provider, ...], tuple[ModelRoute, ...]]:
    """@returns the provider table and the alias table; @raises ConfigError on any inconsistency."""
    if not isinstance(document, dict):
        raise ConfigError("catalog must be a JSON object")
    raw_providers = document.get("providers")
    raw_models = document.get("models")
    if not isinstance(raw_providers, list) or len(raw_providers) == 0:
        raise ConfigError("catalog.providers must be a non-empty list")
    if not isinstance(raw_models, list) or len(raw_models) == 0:
        raise ConfigError("catalog.models must be a non-empty list")

    providers: list[Provider] = []
    seen_providers: set[str] = set()
    for index, entry in enumerate(raw_providers):
        where = f"catalog.providers[{index}]"
        if not isinstance(entry, dict):
            raise ConfigError(f"{where} must be an object")
        provider_id = _identifier(_text(entry, "id", where), f"{where}.id")
        if provider_id in seen_providers:
            raise ConfigError(f"catalog repeats provider id {provider_id!r}")
        seen_providers.add(provider_id)
        base_url = parse_upstream_base_url(_text(entry, "baseUrl", f"provider {provider_id!r}"))
        providers.append(
            Provider(
                id=provider_id,
                display_name=_text(entry, "displayName", f"provider {provider_id!r}", provider_id),
                base_url=base_url,
                key=_provider_key(entry, env, provider_id),
            )
        )

    known = {item.id for item in providers}
    models: list[ModelRoute] = []
    seen_aliases: set[str] = set()
    for index, entry in enumerate(raw_models):
        where = f"catalog.models[{index}]"
        if not isinstance(entry, dict):
            raise ConfigError(f"{where} must be an object")
        alias = _identifier(_text(entry, "alias", where), f"{where}.alias")
        if alias in seen_aliases:
            raise ConfigError(f"catalog repeats model alias {alias!r}")
        seen_aliases.add(alias)
        provider_id = _text(entry, "provider", f"model {alias!r}")
        if provider_id not in known:
            raise ConfigError(f"model {alias!r} names unknown provider {provider_id!r}")
        real_name = _text(entry, "model", f"model {alias!r}")
        if _MODEL_NAME.match(real_name) is None:
            raise ConfigError(f"model {alias!r} has an invalid upstream model name")
        purpose = _text(entry, "purpose", f"model {alias!r}", "llm")
        if purpose not in PURPOSES:
            raise ConfigError(f"model {alias!r} purpose must be one of {sorted(PURPOSES)}")
        models.append(
            ModelRoute(
                alias=alias,
                display_name=_text(entry, "displayName", f"model {alias!r}", real_name),
                provider_id=provider_id,
                real_name=real_name,
                purpose=purpose,
            )
        )
    return tuple(providers), tuple(models)


def load_catalog(path: str, env: Mapping[str, str]) -> tuple[tuple[Provider, ...], tuple[ModelRoute, ...]]:
    """@returns the tables in `path`; missing or malformed files stop the process."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            document = json.load(handle)
    except OSError as error:
        raise ConfigError(f"cannot read ZR_GATEWAY_CATALOG: {error}") from error
    except json.JSONDecodeError as error:
        raise ConfigError(f"ZR_GATEWAY_CATALOG is not valid JSON: {error}") from error
    return parse_catalog(document, env)


def catalog_path(env: Mapping[str, str] | None = None) -> Path | None:
    """@returns the catalog file to load, or None to fall back to the single-upstream variables."""
    source = os.environ if env is None else env
    raw = source.get("ZR_GATEWAY_CATALOG", "").strip()
    return Path(raw).expanduser() if raw != "" else None


def _read_admin_token(env: Mapping[str, str]) -> str:
    token = env.get("ZR_GATEWAY_ADMIN_TOKEN", "").strip()
    if token != "" and len(token) < MIN_ADMIN_TOKEN_LENGTH:
        raise ConfigError(f"ZR_GATEWAY_ADMIN_TOKEN must be at least {MIN_ADMIN_TOKEN_LENGTH} characters")
    return token


def _positive_int(env: Mapping[str, str], name: str, fallback: int) -> int:
    raw = env.get(name, "").strip()
    if raw == "":
        return fallback
    try:
        value = int(raw)
    except ValueError as error:
        raise ConfigError(f"{name} must be an integer") from error
    if value <= 0:
        raise ConfigError(f"{name} must be positive")
    return value


def _positive_float(env: Mapping[str, str], name: str, fallback: float) -> float:
    raw = env.get(name, "").strip()
    if raw == "":
        return fallback
    try:
        value = float(raw)
    except ValueError as error:
        raise ConfigError(f"{name} must be a number") from error
    if value <= 0:
        raise ConfigError(f"{name} must be positive")
    return value


def database_path(env: Mapping[str, str] | None = None) -> str:
    """Database location shared by the server and the admin CLI."""
    source = os.environ if env is None else env
    return source.get("ZR_GATEWAY_DB", "").strip() or "gateway.sqlite3"


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """@returns validated settings; @raises ConfigError with an actionable message."""
    source = os.environ if env is None else env
    path = catalog_path(source)
    providers: tuple[Provider, ...] = ()
    models: tuple[ModelRoute, ...] = ()
    if path is not None:
        providers, models = load_catalog(str(path), source)
        upstream_base_url = providers[0].base_url
        upstream_key = providers[0].key
        model_map = {item.alias: item.real_name for item in models}
    else:
        upstream_base_url = parse_upstream_base_url(source.get("ZR_GATEWAY_UPSTREAM_BASE_URL", "").strip() or DEFAULT_UPSTREAM_BASE_URL)
        upstream_key = _read_key(source)
        model_map = parse_model_map(source.get("ZR_GATEWAY_MODEL_MAP", "").strip() or DEFAULT_MODEL_MAP)
    return Settings(
        upstream_base_url=upstream_base_url,
        upstream_key=upstream_key,
        model_map=model_map,
        db_path=database_path(source),
        token_ttl_seconds=_positive_int(source, "ZR_GATEWAY_TOKEN_TTL_SECONDS", DEFAULT_TOKEN_TTL_SECONDS),
        upstream_timeout_seconds=_positive_float(source, "ZR_GATEWAY_UPSTREAM_TIMEOUT_SECONDS", DEFAULT_UPSTREAM_TIMEOUT_SECONDS),
        mes_base_url=parse_upstream_base_url(source.get("ZR_GATEWAY_MES_BASE_URL", "").strip() or DEFAULT_MES_BASE_URL),
        mes_timeout_seconds=_positive_float(source, "ZR_GATEWAY_MES_TIMEOUT_SECONDS", DEFAULT_MES_TIMEOUT_SECONDS),
        force_include_usage=source.get("ZR_GATEWAY_FORCE_USAGE", "1").strip() != "0",
        providers=providers,
        models=models,
        admin_token=_read_admin_token(source),
    )
