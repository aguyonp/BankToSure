from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from typing import Optional

class Settings(BaseSettings):
    """Application settings loaded from environment."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Fortuneo
    fortuneo_id: str
    fortuneo_pwd: SecretStr
    
    # Sure
    sure_api_key: SecretStr
    sure_account_id: str
    sure_url: str = "http://localhost:3000"
    
    # Discord
    discord_webhook_url: Optional[SecretStr] = None
    
    # AI Categorizer
    groq_api_key: Optional[SecretStr] = None
    category_to_verify: str = "To verify"
    confidence_threshold: int = 80
    
    # App Config
    download_dir: str = "./downloads"
    fetch_days: int = 30
    sync_time: str = "09:00"

settings = Settings()
