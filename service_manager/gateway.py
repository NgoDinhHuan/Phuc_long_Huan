import requests
from config import Cfg

import logging


def get_feature_data(feature_name: str):
    url = f"{Cfg.eme_domain}/api/v1/features/"
    response = requests.get(url, params={"feature_name": feature_name, "api_key": Cfg.eme_api_key})
    if response.status_code == 200:
        return response.json()
    else:
        logging.error("Error: {response.status_code} - {response.text}")
        return None



if __name__ == "__main__":
    feature_name = "HM01"

    feature_data = get_feature_data(feature_name)
    print("Feature Data:", feature_data)