from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    eme_domain: str = "https://emagiceyes.rainscales.com"
    eme_api_key: str = "AI_TiBllikO38zhZFEcednLXQHaIZfIbGVODOlEt4T43XPiVqa8HZsEo3olSq2M3"
    kafka_broker: str = "kafka:9092"
    kafka_topic: str = 'emagic.dvr_videos'

    class Config:
        env_prefix = ''
        case_sensitive = False
        env_file = ".env"

Cfg = Settings()