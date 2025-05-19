import logging
import requests
import sys
from typing import Tuple

from loguru import logger
from pydantic_settings import BaseSettings

from cloud_app.common.log_intercept import InterceptHandler
from enum import Enum


class AppEnvTypes(Enum):
    prod: str = "prod"
    dev: str = "dev"
    test: str = "test"


class BaseAppSettings(BaseSettings):
    app_env: AppEnvTypes = AppEnvTypes.dev

    class Config:
        env_file = ".env"


# class AppConfigs(BaseAppSettings):
#     debug: bool = True

#     # Database configs
#     database_url: str | None = None

#     deploy_env: str = "PRODUCTION"

#     # App configs
#     app_name: str

#     # Kafka params
#     kafka_broker: str
#     kafka_evidence_topic: str
#     kafka_deepstream_topic: str | None = None
#     event_kafka_broker: str = '47.128.81.230:8003'
#     kafka_event_topic: str = 'emagic.events'

#     # Minio configs
#     storage_url: str | None = None
#     storage_domain_url: str | None = None
#     storage_bucket: str | None = None
#     storage_access_key: str | None = None
#     storage_secret_key: str | None = None
#     storage_secure: bool = False

#     # Third party services
#     # MHE10 postprocess event checking
#     mhe10_postprocess_event_checking_url: str = "http://mhe10_postprocess:8089/predict"
#     mhe10_postprocess_event_checking_health_url: str = "http://mhe10_postprocess:8089/health"

#     # Llava_video configs
#     llava_url: str = "llava:8080"
#     mini_backend_api: str = "http://mini_backend:28000/api/v1/features"
#     recheck_with_llava: str = (
#         "PAR01,PAR02,HM01,HM02,HM03,HM05,PPE01,PPE02,PRD01,PL01"
#     )
#     event_extend_bbox: dict = {
#         "PAR01": [1.5, 0.5],
#         "HM01": [1.5, 0.5],
#         "HM02": [1.5, 0.5],
#         "HM03": [1.5, 0.5],
#         "HM05": [1, 0.5],
#         "PRD01": [1.5, 0.5]
#     }

#     # max time for event in seconds
#     max_time_for_event: dict = {
#         "HM01": 5,
#         "HM02": 5,
#         "HM03": 5,
#         "HM05": 5,
#         "HM07": 5,
#         "HM08": 5,
#         "MHE01": 5,
#         "MHE03": 5,
#         "MHE04": 5,
#         "MHE07": 5,
#         "MHE08": 5,
#         "MHE09": 5,
#         "MHE10": 5,
#         "OTH02": 5,
#         "PAR01": 5,
#         "PAR02": 5,
#         "PAR03": 5,
#         "PERSON_FALLDOWN": 5,
#         "PL02": 10,
#         "PL03": 5,
#         "PPE01": 5,
#         "PPE02": 5,
#         "PRD01": 5,
#         "VEH01": 10,
#         "VEH02": 10,
#         "VEH03": 10
#     }

#     fps_for_event: dict = {
#         "HM01": 60,
#         "HM02": 60,
#         "HM03": 60,
#         "HM05": 60,
#         "HM07": 60,
#         "HM08": 60,
#         "MHE01": -1,
#         "MHE03": -1,
#         "MHE04": 60,
#         "MHE07": 60,
#         "MHE08": 60,
#         "MHE09": 60,
#         "MHE10": -1,
#         "OTH02": 60,
#         "PAR01": 60,
#         "PAR02": 60,
#         "PAR03": 60,
#         "PERSON_FALLDOWN": 60,
#         "PL02": 60,
#         "PL03": 60,
#         "PPE01": 60,
#         "PPE02": 60,
#         "PRD01": 60,
#         "VEH01": 60,
#         "VEH02": 60,
#         "VEH03": 60
#     }

#     event_type_names: dict = {
#         'MHE01': 'COLLISION',
#         'HM01': 'CLIMBJPTRUCK',
#         'HM02': 'CLIMBJPDOCK',
#         'MHE03': 'MCROSSR',
#         'MHE09': 'NVISIBLE',
#         'MHE10': 'LOADHIGH',
#         'MHE04': 'MOVE8PALLETS',
#         'PAR01': 'OUSEPHONE',
#         'PAR02': 'USEPHONE',
#         'HM03': 'CLIMBPRO',
#         'HM05': 'NWALKWAY',
#         'HM07': 'SIT2M',
#         'PL02': 'PALLETONF',
#         'PL03': 'PALLETONF_PLUS',
#         'OTH02': 'ALCOHOLTEST',
#         'PRD01': 'PRFLOOR',
#         'VEH03': 'TRUCKLOADING',
#         'PPE02': 'NSAFESHOE'
#     }

    
#     eme_domain: str = "https://emagiceyes.rainscales.com"
#     eme_api_key: str = "AI_TiBllikO38zhZFEcednLXQHaIZfIbGVODOlEt4T43XPiVqa8HZsEo3olSq2M3"

#     # Log configs
#     logging_level: int = logging.INFO
#     loggers: Tuple[str, str] = ("uvicorn.asgi", "uvicorn.access")

#     camera_config_update_interval: int = 60

#     eme_events_collector_url: str | None = None

#     class Config:
#         validate_assignment = True

#     def configure_logging(self) -> None:
#         logging.getLogger().handlers = [InterceptHandler()]
#         for logger_name in self.loggers:
#             logging_logger = logging.getLogger(logger_name)
#             logging_logger.handlers = [
#                 InterceptHandler(level=self.logging_level)
#             ]

#         logger.configure(
#             handlers=[{"sink": sys.stderr, "level": self.logging_level}]
#         )


# cfg = AppConfigs()


# def get_feature_config(feature_name: str):
#     url = cfg.mini_backend_api + f"/{feature_name}"
#     return requests.get(url).json()
from typing import Optional
class AppConfigs(BaseAppSettings):
    app_name: Optional[str] = None
    kafka_broker: Optional[str] = None
    kafka_evidence_topic: Optional[str] = None
    event_kafka_broker: str = '******'
 
    class Config:
        extra = "ignore"  # Bỏ qua các trường không hợp lệ
cfg = AppConfigs()
 
 
def get_feature_config(feature_name: str):
    url = cfg.mini_backend_api + f"/{feature_name}"
    return requests.get(url).json()