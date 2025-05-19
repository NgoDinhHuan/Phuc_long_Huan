import requests
from .config import Cfg


def get_ai_models(skip: int=0, limit: int=0):
    url = f"{Cfg.eme_domain}/api/v1/ai_models"
    response = requests.get(url, params={"api_key": Cfg.eme_api_key, "skip": skip, "limit": limit})

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def get_camera_config(camera_key: str):
    url = f"{Cfg.eme_domain}/api/v1/cameras/config_map/"
    response = requests.get(url, params={"camera_key": camera_key, "api_key": Cfg.eme_api_key})
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def get_feature_config_map(feature_name: str):
    url = f"{Cfg.eme_domain}/api/v1/features/config_map/"
    response = requests.get(url, params={"feature_name": feature_name, "api_key": Cfg.eme_api_key})
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def get_feature_data(feature_name: str):
    url = f"{Cfg.eme_domain}/api/v1/features/"
    response = requests.get(url, params={"feature_name": feature_name, "api_key": Cfg.eme_api_key})
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def get_camera_by_key(camera_key: str):
    url = f"{Cfg.eme_domain}/api/v1/cameras/"
    response = requests.get(url, params={"camera_key": camera_key, "api_key": Cfg.eme_api_key})
    if response.status_code == 200:
        response = response.json()
        return response
    else:
        return None