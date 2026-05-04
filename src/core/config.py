from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Pose API (B53)"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Credenciales a Hetzner (Postgres PROD)
    PG_HOST: str = "10.10.0.1"
    PG_PORT: str = "5432"
    PG_USER: str = "pose_admin"
    PG_PASS: str = "PoseAdmin2026!"
    PG_DB_PROD: str = "dw_grupopose_b52_prod"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql://{self.PG_USER}:{self.PG_PASS}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB_PROD}"

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )


settings = Settings()
