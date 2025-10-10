from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:2410@localhost:5432/lets_credo_database"
    JWT_SECRET_KEY: str = "ksdZwwWsLw"  # Should match auth_service's key for token validation
    JWT_ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"

settings = Settings()