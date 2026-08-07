from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # Database
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Storage & Payments
    UPLOAD_DIR: str
    SITE_URL: str
    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str

    # Blue Dart Credentials & Defaults
    BLUEDART_ENV: str = "production"
    BLUEDART_BASE_URL: str = "https://apigateway.bluedart.com"
    BLUEDART_AUTH_URL: str = "https://apigateway.bluedart.com/in/transportation/token/v1/login"
    BLUEDART_CLIENT_ID: str
    BLUEDART_CLIENT_SECRET: str
    BLUEDART_LOGIN_ID: str
    BLUEDART_LICENSE_KEY: str
    BLUEDART_CUSTOMER_CODE: str
    BLUEDART_ORIGIN_AREA: str = "GUN"
    BLUEDART_DEFAULT_PRODUCT: str = "A"
    BLUEDART_DEFAULT_SUBPRODUCT: str = "P"
    BLUEDART_TIMEOUT_MS: int = 55000

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()