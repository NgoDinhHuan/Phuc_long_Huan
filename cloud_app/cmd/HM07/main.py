"""
Person inactive more than 5 minutes
"""

import json
import asyncio

import faust
from loguru import logger

from cloud_app.common.config import cfg
from cloud_app.common.message_parser import MessageParser
from cloud_app.internal.controller.hm07.camera import Camera
from cloud_app.internal.controller.hm07.detection import Detection
from cloud_app.gateway.contract.pgdb import get_feature_data_in_local


logger.add(f'/logs/{cfg.app_name}' + '_{time:YYYY-MM-DD}.log',
           format="{time} {level} {message}",
           level="INFO",
           rotation="00:00",  # split log file at midnight
           retention="30 days",  # keep log file for 30 days
           enqueue=True
           )
logger.info(f"Start {cfg.app_name} service")

app = faust.App(
    cfg.app_name, broker=cfg.kafka_broker, consumer_auto_offset_reset="latest"
)
consume_topic = app.topic(cfg.kafka_deepstream_topic, key_type=bytes, value_type=bytes)
producer_topic = app.topic(cfg.kafka_evidence_topic, key_type=bytes, value_type=bytes)

cameras: dict[str, Camera] = {}


def update_cam_config(config_map):
    global cameras

    for cam_id, config in config_map.items():
        if cam_id in cameras:
            cameras[cam_id].config = config
            logger.info(f"Camera {cam_id} updated")
        else:
            camera = Camera(cam_id, config)
            cameras[cam_id] = camera
            logger.info(f"Camera {cam_id} created")


    # for cam_id, camera in list(cameras.items()):
    #     if cam_id not in config_map:
    #         logger.warning(f"Cam {cam_id} is not in config map.--->>> Remove it out of cameras")
    #         del cameras[cam_id]

@app.task()
async def init_camera_config():
    config_map = get_feature_data_in_local(cfg.app_name)
    if config_map is None:
        logger.error(f"Feature {cfg.app_name} is not found")
        return
    if len(config_map) == 0:
        logger.warning(f"Feature {cfg.app_name} is empty --->>>> Disable feature")

    update_cam_config(config_map)


@app.agent(consume_topic)
async def consumer(messages):
    async for msg_key, message in messages.items():
        all_config_map = message.get("extra_information", {}).get("detectionRules", [])
        new_config_map = list(filter(lambda c: c["ruleCode"] == cfg.app_name, all_config_map))
        camera_id = message.get("extra_information", {}).get("cameraCode", None)

        if len(new_config_map) > 0:
            new_config = {camera_id: new_config_map[0]["ruleConfig"]}
            update_cam_config(new_config)

        elif camera_id not in cameras:
            logger.warning(f"Skip message because there is no config for camera {camera_id} in feature {cfg.app_name}.")
            continue

        # updated_rules = message.get("extra_information", {}).get("newUpdatedRules", [])
        # if cfg.app_name not in all_active_rules:
        #     logger.warning(f"Feature {cfg.app_name} is disabled, restart service")
        #
        #     await asyncio.sleep(10)
        #     continue

        # if cfg.app_name in updated_rules:
        #     await update_camera_config()

        msg_data = MessageParser.parse_message(message)
        # logger.info(msg_data)
        if not msg_data.is_ok:
            logger.error(f"Message is not valid: {msg_data}")
            continue
        cam_id = msg_data.cam_id
        frame_id = msg_data.frame_id
        video_url = msg_data.video_url
        extra_information = msg_data.extra_information

        camera = cameras.get(cam_id)
        if not camera:
            # logger.error(f"Cam {cam_id} is not in cameras")
            continue
        image_size = camera.config.get("cam_resolution", (1920, 1080))
        detections = [
            Detection(
                msg=det,
                frame_id=frame_id,
                cam_id=cam_id,
                video_url=video_url,
                image_size=image_size,
                extra_information=extra_information
            )
            for det in msg_data.detections if det["class_name"] in camera.config["target_class"]
        ]
        camera.update_tracks(
            detections=detections, frame_id=frame_id, video_url=video_url
        )
        event_detections, event_confs, _ = camera.event_checking(frame_id=frame_id)
        if event_detections:
            for event_detection, event_conf in zip(event_detections, event_confs):
                msg = camera.create_event(
                    event_name=cfg.app_name,
                    detections=event_detection,
                    event_conf=event_conf,
                    frame_id=frame_id,
                    push_time=msg_data.push_time
                )
                await producer_topic.send(value=json.dumps(msg).encode("utf-8"), key=msg_key)
                logger.info(f"DETECTED EVENT {cfg.app_name} at frame {frame_id} cam {cam_id} video {video_url}")
