import secrets
from pathlib import Path
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"

_KNOWN_WEAK_SECRET_KEYS = frozenset({"dev-secret-key-change-in-production"})


class Settings(BaseSettings):
    # 相对 cwd 的 ".env" 在 systemd 下常找不到；锚定 backend 目录。
    # 无 .env 时开发环境自动生成进程内密钥，避免远端导入即 ValidationError → 502。
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./erp.db"
    # WorkBuddy MES 连接器常只配置密码，用户名留空时使用
    mes_default_username: str = "admin"

    @model_validator(mode="after")
    def _ensure_secret_key(self) -> Self:
        env = self.app_env.strip().lower()
        is_production = env in ("production", "prod")

        if is_production:
            if (
                not self.secret_key
                or self.secret_key in _KNOWN_WEAK_SECRET_KEYS
                or len(self.secret_key) < 32
            ):
                raise ValueError(
                    "SECRET_KEY must be set to a secure value (>= 32 characters) in production"
                )
            return self

        if not self.secret_key or self.secret_key in _KNOWN_WEAK_SECRET_KEYS:
            object.__setattr__(self, "secret_key", secrets.token_urlsafe(32))
        return self


settings = Settings()
