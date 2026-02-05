import streamlit as st


class Settings:
    # Application
    APP_NAME: str = "UPSC Expert Verification Tool"
    DEBUG: bool = False

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @property
    def DB_HOST(self) -> str:
        return st.secrets["DB_HOST"]

    @property
    def DB_PORT(self) -> int:
        return int(st.secrets["DB_PORT"])

    @property
    def DB_NAME(self) -> str:
        return st.secrets["DB_NAME"]

    @property
    def DB_USERNAME(self) -> str:
        return st.secrets["DB_USERNAME"]

    @property
    def DB_PASSWORD(self) -> str:
        return st.secrets["DB_PASSWORD"]

    @property
    def DATABASE_URL(self) -> str:
        """Build database URL from separate credentials."""
        return f"postgresql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
