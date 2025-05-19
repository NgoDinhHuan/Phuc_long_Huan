from pydantic.v1 import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    eme_domain: str = "https://emagiceyes.rainscales.com"
    eme_api_key: str = "AI_TiBllikO38zhZFEcednLXQHaIZfIbGVODOlEt4T43XPiVqa8HZsEo3olSq2M3"
    network_name: Optional[str] = "eme_network"
    project_name: Optional[str] = "mge-ai-deploy-dev"
    check_health_interval: int = 60
    check_db_status_interval: int = 60

    class Config:
        env_prefix = ''
        case_sensitive = False
        env_file = ".env"

Cfg = Settings()