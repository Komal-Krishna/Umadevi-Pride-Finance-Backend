from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Supabase Configuration
    supabase_url: str
    supabase_key: str
    supabase_service_key: str
    
    # JWT Configuration
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Application Configuration
    app_name: str = "UmaDevis Pride Finance Management"
    debug: bool = True
    environment: str = "development"
    
    # Master Password
    master_password: str
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
