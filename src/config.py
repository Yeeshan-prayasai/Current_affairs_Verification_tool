from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
import streamlit as st


class Settings(BaseSettings):
    # Database - separate credentials
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "prayas"
    DB_USERNAME: str = "postgres"
    DB_PASSWORD: str = ""

    # Application
    APP_NAME: str = "UPSC Expert Verification Tool"
    DEBUG: bool = False

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @property
    def DATABASE_URL(self) -> str:
        """Build database URL from separate credentials."""
        return f"postgresql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    # Check if running on Streamlit Cloud (secrets available)
    try:
        if hasattr(st, 'secrets') and 'DB_HOST' in st.secrets:
            return Settings(
                DB_HOST=st.secrets["DB_HOST"],
                DB_PORT=int(st.secrets["DB_PORT"]),
                DB_USERNAME=st.secrets["DB_USERNAME"],
                DB_PASSWORD=st.secrets["DB_PASSWORD"],
                DB_NAME=st.secrets["DB_NAME"],
            )
    except Exception:
        pass
    # Fallback to .env file for local development
    return Settings()


settings = get_settings()
