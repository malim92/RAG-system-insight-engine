from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "InsightEngine AI Service"
    debug: bool = False
    
    openai_api_key: str = ""
    gemini_api_key: str
    
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents"
    
    redis_host: str = "localhost"
    redis_port: int = 6379

    backend_url: str = "http://localhost:8080"

    # LLM provider: "gemini" (free tier), "ollama" (local), or "openai" (paid)
    llm_provider: str = "gemini"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    gemini_model: str = "gemini-3-flash-preview"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
