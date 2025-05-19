from loguru import logger as logging
from tools.pgdb import get_ai_models, get_feature_data


def get_model_ai_features_mapping(except_model=[]):
    ai_model_infos = get_ai_models()["data"]
    ai_models_mapping = { model["name"] : model["features"] for model in ai_model_infos}
    if except_model:
        for model in except_model:
            del ai_models_mapping[model]
    return ai_models_mapping

def get_feature_cameras_mapping(all_features):
    outputs = {}
    for feat_name in all_features:
        if feat_name not in outputs:
            response = get_feature_data(feat_name)
            outputs[feat_name] = list(response["config_map"].keys())
    return outputs


def get_ds_topic_cameras_mapping(mapping, feature_cameras_mapping):
    outputs = {}
    for key, value in mapping.items():
        if key not in outputs:
            camera_names = []
            for f_name in value:
                camera_names.extend(feature_cameras_mapping[f_name])
            outputs[key] = list(set(camera_names))

    camera_topics_mapping = {}
    for key, value in outputs.items():
        for camera_name in value:
            if camera_name not in camera_topics_mapping:
                camera_topics_mapping[camera_name] = [key]
            else:
                camera_topics_mapping[camera_name].append(key)
    return camera_topics_mapping