from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # Database
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Storage
    UPLOAD_DIR: str
    SITE_URL: str
    RAZORPAY_KEY_ID: str

    RAZORPAY_KEY_SECRET: str


    class Config:
        env_file = ".env"


settings = Settings()