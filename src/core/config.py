from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Pose API (B52)"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Credenciales a PostgreSQL.
    # En Docker (Hetzner): sobrescritos por env vars del docker-compose.
    # En local (M1 vía WireGuard): usan los defaults de abajo.
    DB_HOST: str = "10.10.0.1"
    DB_PORT: str = "5432"
    DB_USER: str = "pose_admin"
    DB_PASSWORD: str = "PoseAdmin2026!"
    DB_NAME: str = "dw_grupopose_b52_prod"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )


settings = Settings()
