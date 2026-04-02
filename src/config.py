from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """Application settings loaded from environment."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Fortuneo
    fortuneo_id: str
    fortuneo_pwd: str
    
    # Sure
    sure_api_key: str
    sure_account_id: str
    sure_url: str = "http://localhost:3000"
    
    # Discord
    discord_webhook_url: Optional[str] = None
    
    # App Config
    download_dir: str = "./downloads"
    fetch_days: int = 30
    sync_time: str = "09:00"

settings = Settings()
