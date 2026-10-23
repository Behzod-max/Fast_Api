from pydantic_settings import BaseSettings, SettingsConfigDict


class IlovaSozlamalari(BaseSettings):
    """Ilova sozlamalarini muhit o‘zgaruvchilari va `.env` faylidan o‘qiydi."""

    APP_NAME: str = "E-commerce API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = IlovaSozlamalari()
from pydantic_settings import BaseSettings, SettingsConfigDict


class IlovaSozlamalari(BaseSettings):
    APP_NAME: str = "E-commerce API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: list[str] = []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = IlovaSozlamalari()
