from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./dev.db"
    jwt_secret: str = "dev-secret-change-me-dev-secret-change-me"
    jwt_ttl_hours: int = 24
    demo_password: str = "demo1234!"
    storage_backend: str = "local"  # local | s3
    upload_dir: str = "./uploads"
    s3_bucket: str = ""
    s3_region: str = "ap-northeast-2"
    s3_endpoint: str = ""  # MinIO 등 S3 호환 저장소. 비우면 AWS
    rate_limit_login: str = "20/minute"
    rate_limit_upload: str = "10/minute"
    cors_origins: str = "http://localhost:5173"
    minimum_wage_hourly: int = 10320
    seed_on_empty: bool = True


settings = Settings()
