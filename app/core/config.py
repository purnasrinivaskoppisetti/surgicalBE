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

    # FTP

    FTP_HOST: str
    FTP_PORT: int

    FTP_USERNAME: str
    FTP_PASSWORD: str

    FTP_ROOT_DIR: str
    FTP_UPLOAD_DIR: str

    SITE_URL: str

    class Config:
        env_file = ".env"


settings = Settings()