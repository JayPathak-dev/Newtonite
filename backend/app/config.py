from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+psycopg://newtonite:newtonite_dev_password@localhost:5435/newtonite_ops"
    TEST_DATABASE_URL: str = "postgresql+psycopg://newtonite:newtonite_dev_password@localhost:5436/newtonite_ops_test"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production-32-chars-min"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000"

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.is_production:
            if not self.SECRET_KEY or self.SECRET_KEY == "dev-secret-key-change-in-production-32-chars-min":
                raise ValueError("In production, SECRET_KEY must be set to a secure, unique secret!")
            if len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters long.")
        return self


settings = Settings()

