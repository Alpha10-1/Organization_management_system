import os


class Settings:
    APP_NAME = "Organization Management System API"
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours


settings = Settings()