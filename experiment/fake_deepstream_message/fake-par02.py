import os
import json
import sys
import cv2
import argparse
import supervision as sv
from datetime import datetime
from ultralytics import YOLO

sys.path.append("../../")
from cloud_app.common.config import cfg
from cloud_app.gateway.contract.kafka import init_kafka_producer


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="RainScale")
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--video_url", type=str, required=True)
    parser.add_argument("--cam_id", type=str, default="cam1")
    parser.add_argument(
        "--save_video_dir",
        type=str,
        default="/home/duongpd/trungnt/MGE/mge_ai_cloud/test_volumes/output",
    )
    kafka_producer = init_kafka_producer(cfg.kafka_broker)
    args = parser.parse_args()
    frame_id = 0
    yolo = YOLO(args.model)
    video_url = args.video_url
    cam_id = args.cam_id
    cap = cv2.VideoCapture(video_url)

    print("Input video url: {}".format(video_url))
    while cap.isOpened():
        frame_id += 1
        print(frame_id)
        ret, frame = cap.read()
        if frame_id % 3 != 0:
            continue
        if not ret:
            break

        h, w, _ = frame.shape
        results = yolo(frame)[0]
        detections = sv.Detections.from_ultralytics(results)
        print("Number of detection {}".format(len(detections)))
        detection_data = []
        xyxy_list = detections.xyxy.tolist()
        confidence_scores = detections.confidence.tolist()
        class_ids = detections.class_id.tolist()
        class_names = detections.data["class_name"].tolist()

        for i in range(len(xyxy_list)):
            print(class_names)
            if not class_names[i] == "person":
                continue
            try:
                detection_data.append(
                    {
                        "xyxy": xyxy_list[i],
                        "confidence": confidence_scores[i],
                        "class_id": class_ids[i],
                        "class_name": class_names[i],
                        "frame_id": frame_id,
                        "cam_id": args.cam_id,
                        "detect_time": frame_id,
                        "push_time": datetime.now().strftime(
                            "%d/%m/%y %H:%M:%S"
                        ),
                        "video_url": video_url,
                        "using_phone_scores": 0.8,
                        "attach_phone_scores": 0.8,
                    }
                )
            except Exception as e:
                print(e)

        message = {
            "cam_id": args.cam_id,
            "frame_id": frame_id,
            "video_url": video_url,
            "detections": detection_data,
            "push_time": datetime.now().strftime("%d/%m/%y %H:%M:%S"),
        }
        kafka_producer.send(
            cfg.kafka_deepstream_topic, json.dumps(message).encode("utf-8")
        )
        kafka_producer.flush()
        print(
            "Send event to broker {} with topic {}".format(
                cfg.kafka_broker, cfg.kafka_deepstream_topic
            )
        )

        # cv2.imshow("output", frame)
        # if cv2.waitKey(1) == ord("q"):
        #     saved_video.release()
        #     break
