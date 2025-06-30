"""
Configuration settings for the QA System
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # App settings
    app_name: str = "QA System"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Google Gemini settings
    google_api_key: str = Field(..., env="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", env="GEMINI_MODEL")
    
    # Database settings
    database_url: str = Field(default="sqlite:///./data/database/qa_system.db", env="DATABASE_URL")
    
    # File upload settings
    upload_folder: str = Field(default="./data/uploads", env="UPLOAD_FOLDER")
    max_file_size: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    allowed_extensions: list[str] = Field(default=["pptx", "ppt"], env="ALLOWED_EXTENSIONS")
    
    # API settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    
    # QA Generation settings
    qa_per_slide: int = Field(default=1, env="QA_PER_SLIDE")  # Reduced to 1 question to reduce processing load
    max_slides_for_qa: int = Field(default=10, env="MAX_SLIDES_FOR_QA")  # Maximum 10 slides
    difficulty_levels: list[str] = Field(default=["easy", "medium", "hard"], env="DIFFICULTY_LEVELS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DATABASE_DIR = DATA_DIR / "database"

# Create directories
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_DIR.mkdir(parents=True, exist_ok=True)