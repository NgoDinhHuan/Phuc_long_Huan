import requests
from cloud_app.common.config import cfg
from loguru import logger

def get_camera_config(camera_key: str):
    try:
        url = f"{cfg.eme_domain}/api/v1/cameras/config_map/"
        response = requests.get(url, params={"camera_key": camera_key, "api_key": cfg.eme_api_key})
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        raise e


def get_feature_config_map(feature_name: str):
    try:
        url = f"{cfg.eme_domain}/api/v1/features/config_map/"
        response = requests.get(url, params={"feature_name": feature_name, "api_key": cfg.eme_api_key})
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        raise e

def get_feature_data(feature_name: str):
    try:
        url = f"{cfg.eme_domain}/api/v1/features/"
        response = requests.get(url, params={"feature_name": feature_name, "api_key": cfg.eme_api_key})
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        raise e


def get_camera_by_key(camera_key: str):
    try:
        url = f"{cfg.eme_domain}/api/v1/cameras/"
        response = requests.get(url, params={"camera_key": camera_key, "api_key": cfg.eme_api_key})
        if response.status_code == 200:
            response = response.json()
            return response
        else:
            return None
    except Exception as e:
        raise e

def get_camera_tenant_area(camera_key: str):
    try:
        response = get_camera_by_key(camera_key)
        if response is not None:
            tenant_id = response["area"]["tenant"]["id"]
            area_name = response["area"]["name"]
            outputs = {
                "tenant_id": tenant_id,
                "area_name": area_name
            }
        else:
            logger.warning(f"Tenant and area of camera key: {camera_key} not exist in database.")
            outputs = {
                "tenant_id": "default",
                "area_name": "default"
            }
        return outputs
    except Exception as e:
        logger.error(f"Error when fetching camera key: {camera_key} information: {str(e)}")
        return {
                "tenant_id": "default",
                "area_name": "default"
            }