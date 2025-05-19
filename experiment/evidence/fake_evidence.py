import os
import sys
import json
import cv2
import faust
import imageio
from datetime import datetime

sys.path.append("../../")

from cloud_app.common.config import cfg, get_feature_config
from cloud_app.gateway.contract.kafka import init_kafka_producer
from cloud_app.internal.pkg.box import (
    draw_bb,
    crop_image_with_padding,
    get_union_box,
)


if __name__ == "__main__":
    app_name = "par02"
    print(
        "Send Kafka message to broker {} with topic:  {}".format(
            cfg.kafka_broker,
            cfg.kafka_evidence_topic,
        )
    )
    fake_message = {
        "name": "PAR02",
        "detections": [
            {
                "confidence": 0.6798045039176941,
                "class_id": 0,
                "class_name": "forklift",
                "track_id": 48,
                "bbox": [200, 200, 600, 600],
                "detect_time": 1723266934.501912,
                "frame_id": 1206,
                "cam_id": "7297170438710103",
                "video_url": "/app/test_volumes/dvr_test_video/rainscale11.mp4",
            },
            {
                "confidence": 0.6798045039176941,
                "class_id": 0,
                "class_name": "forklift",
                "track_id": 49,
                "bbox": [200, 200, 600, 600],
                "detect_time": 1723266934.501912,
                "frame_id": 10,
                "cam_id": "7297170438710103",
                "video_url": "/app/test_volumes/dvr_test_video/employee_entrance.mp4",
            },
        ],
        "camera_id": "7297170438710103",
        "push_time": str(datetime.now()),
        "frame_id": 1218,
    }
    kafka_producer = init_kafka_producer(cfg.kafka_broker)
    kafka_producer.send(
        cfg.kafka_evidence_topic, json.dumps(fake_message).encode("utf-8")
    )
    kafka_producer.flush()
    print("Done")
