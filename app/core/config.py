from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    ECHO_SQL: bool = False

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
