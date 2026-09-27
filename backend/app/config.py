from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./erp.db"
    # WorkBuddy MES 连接器常只配置密码，用户名留空时使用
    mes_default_username: str = "admin"


settings = Settings()
