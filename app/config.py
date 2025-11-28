from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List

class Settings(BaseSettings):
    #PostgreSQL Settings
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str

    # ChromaDB Settings
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    CHROMA_COLLECTION_NAME: str = "interview_questions"

    # Application Settings
    API_VERSION: str = "v1"
    DEBUG: bool = False

    # Gemini API Settings
    GEMINI_API_KEY: str  # Add this line
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_TEMPERATURE: float = 0.7  # Add this line
    GEMINI_MAX_TOKENS: int = 1000  # Add this line

    # Similarity threshold for duplicate detection
    SIMILARITY_THRESHOLD: float = 0.85  # Add this line

    class Config:
        env_file = '/Users/disha/PycharmProjects/ai-mock-interview/.env'

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


@lru_cache()
def get_settings():
    """Cache settings to avoid repeated file reads"""
    return Settings()
