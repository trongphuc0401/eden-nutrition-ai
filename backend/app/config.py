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
    report_rate_limit_per_hour: int = 10
    reference_data_source: str = "auto"  # auto | db | json
    reference_min_db_ingredients: int = 20
    reference_cache_seconds: int = 300
    pdf_output_dir: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:3000/api/v1/auth/google/callback"
    session_secret: str | None = None
    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def google_auth_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret and self.session_secret)

    @property
    def pdf_dir(self) -> Path:
        if self.pdf_output_dir:
            return Path(self.pdf_output_dir)
        return Path(__file__).resolve().parents[2] / "output" / "pdf"

    def validate_production(self) -> None:
        if not self.is_production:
            return
        missing = [
            name
            for name, value in (
                ("SESSION_SECRET", self.session_secret),
                ("GOOGLE_CLIENT_ID", self.google_client_id),
                ("GOOGLE_CLIENT_SECRET", self.google_client_secret),
                ("ZAI_API_KEY", self.zai_api_key),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(f"APP_ENV=production requires: {', '.join(missing)}")
        if self.report_recipe_mode.strip().lower() == "mock":
            raise RuntimeError("APP_ENV=production must not use REPORT_RECIPE_MODE=mock")
        if len(self.session_secret or "") < 32:
            raise RuntimeError("SESSION_SECRET must be at least 32 characters")


settings = Settings()
