from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    ECHO_SQL: bool = False

    # JWT Settings - Es crucial que SECRET_KEY se gestione de forma segura y no esté hardcodeada.
    # Idealmente, cárgala desde el archivo .env
    SECRET_KEY: str = "e8b8a3c8f2d6b5a9d4e7f1a2b3c4d5e6f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
