"""
"""

import json
import asyncio

import faust
from loguru import logger

from cloud_app.common.config import cfg
from cloud_app.common.message_parser import MessageParser
from cloud_app.gateway.contract.kafka import init_kafka_producer
from cloud_app.internal.controller.CLEAN.camera import Camera
from cloud_app.internal.controller.CLEAN.detection import Detection
from cloud_app.gateway.contract.pgdb import get_camera_tenant_area, get_feature_data


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

STATUS = True
cameras: dict[str, Camera] = {}


@app.timer(interval=cfg.camera_config_update_interval)
async def update_camera_config():
    global STATUS

    try:
        feature = get_feature_data(cfg.app_name)
        if not feature:
            logger.error(f"Feature {cfg.app_name} is not found")
            return
    except Exception as e:
        logger.error(f"Failed to fetch feature data for {cfg.app_name}: {e}")
        return

    if feature.get("status") is not None:
        STATUS = bool(feature.get("status"))

    config_map = feature.get("config_map")
    if len(config_map) == 0:
        logger.error(f"{cfg.app_name} --- Config map is empty")
        STATUS = False

    for cam_id, config in config_map.items():
        try:
            tenant_area_info = get_camera_tenant_area(cam_id)
            config.update(tenant_area_info)
        except Exception as e:
            logger.error(f"Failed to fetch tenant area info for cam {cam_id}: {e}")
            continue

        if cam_id in cameras:
            cameras[cam_id].config = config
        else:
            camera = Camera(cam_id, config)
            cameras[cam_id] = camera

    for cam_id, camera in list(cameras.items()):
        if cam_id not in config_map:
            logger.warning(f"Cam {cam_id} is not in config map")
            del cameras[cam_id]


@app.agent(consume_topic)
async def consumer(messages):
    while not cameras:
        logger.warning(f"Waiting for load camera config for {cfg.app_name}")
        await asyncio.sleep(60)
        
    global STATUS
    while not STATUS:
        logger.warning(f"Feature {cfg.app_name} is disabled, waiting for enable")
        # Check every 3 minutes
        await asyncio.sleep(180)

    async for msg_key, message in messages.items():
        if not STATUS:
            logger.warning(f"Feature {cfg.app_name} is disabled, restart service")
            break

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
            for det in msg_data.detections
        ]
        camera.update_tracks(
            detections=detections, frame_id=frame_id, video_url=video_url
        )
        #TODO: checks for event return multiple evidence
        event_detections, event_confs, _ = camera.event_checking(frame_id=frame_id)
        if event_detections:
            msg = camera.create_event(
                event_name=cfg.app_name,
                detections=event_detections,
                event_conf=event_confs[0],
                frame_id=frame_id,
                push_time=msg_data.push_time
            )
            await producer_topic.send(value=json.dumps(msg).encode("utf-8"), key=msg_key)
            logger.info(f"DETECTED EVENT {cfg.app_name} at frame {frame_id} cam {cam_id} video {video_url}")
