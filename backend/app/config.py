from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    anthropic_model_fast: str = "claude-haiku-4-5"
    anthropic_model_deep: str = "claude-sonnet-4-6"
    database_url: str = "sqlite:///./literaturki.db"
    upload_dir: str = "./uploads"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
