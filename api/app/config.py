from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://estimate:change_me@localhost:5432/ai_estimate"
    jwt_secret: str = "dev-secret"
    jwt_expiry_hours: int = 8
    ai_provider: str = "openai"
    ai_model: str = "gpt-4o"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    hermes_url: str = "http://localhost:8080"
    storage_backend: str = "local"
    storage_path: str = "./data"
    default_locale: str = "ja"
    app_env: str = "development"


settings = Settings()
