from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Nutrition Coach API"
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_nutrition"
    cors_allow_origins: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    llm_provider: str = "gemini"
    llm_api_key: str | None = None
    llm_model: str = "gemini-2.0-flash"
    llm_base_url: str | None = None
    embedding_provider: str = "openai"
    embedding_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_base_url: str | None = None
    embedding_dimensionality: int = 1536
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    zai_api_key: str | None = None
    zai_model: str = "glm-4.7-flash"
    zai_base_url: str = "https://api.z.ai/api/paas/v4"
    report_recipe_mode: str = "mock"
    report_model_timeout_seconds: int = 45
    report_model_max_retries: int = 1
    report_recipe_max_repairs: int = 2
    report_job_active_timeout_seconds: int = 180
    report_job_persistence_enabled: bool = False
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:8000/v1/auth/google/callback"
    session_secret: str | None = None
    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


settings = Settings()
