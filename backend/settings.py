from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ai_mode: Literal["mock", "live"] = "mock"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_origin: str = "http://localhost:5173"
    storage_dir: str = "data"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
