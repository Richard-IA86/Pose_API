from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Pose_API"
    app_env: str = "development"
    debug: bool = True

    # JWT
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database
    database_url: str = "sqlite:///./pose.db"

    # CORS — comma-separated list of allowed origins, e.g. "https://app.example.com"
    # Use "*" only for development
    cors_origins: str = "*"

    # ETL service
    etl_base_url: str = "http://localhost:8001"
    etl_api_key: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_production_settings(self) -> None:
        """Raise an error if unsafe defaults are detected in non-development environments."""
        if self.app_env != "development" and self.secret_key == "change-me-in-production":
            raise RuntimeError(
                "SECRET_KEY must be set to a strong random value in non-development environments."
            )


settings = Settings()
