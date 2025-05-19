import argparse
import json
from datetime import datetime

import cv2
import supervision as sv
from kafka import KafkaProducer
from ultralytics import YOLO


def init_kafka_producer(bootstrap_server: str) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=[bootstrap_server],
        request_timeout_ms=5000,
        max_block_ms=5000,
    )


kafka_producer = init_kafka_producer("47.128.81.230:8003")
polygons = (
    [
        [[211, 961], [1472, 279], [1909, 384], [1909, 982]],
        [[215, 921], [1442, 229], [1109, 382], [1979, 912]],
    ],
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="RainScale")
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--video_url", type=str, required=True)
    parser.add_argument("--cam_id", type=str, default="cam1")

    args = parser.parse_args()
    frame_id = 0
    yolo = YOLO(args.model)
    yolo.conf = 0.65  # NMS confidence threshold
    yolo.iou = 0.45  # NMS IoU threshold
    yolo.agnostic = False  # NMS class-agnostic
    yolo.multi_label = False  # NMS multiple labels per box
    yolo.max_det = 1000  # maximum number of detections per image
    print("------------")
    print(yolo.names)

    video_url = args.video_url
    cam_id = args.cam_id
    cap = cv2.VideoCapture(video_url)

    while cap.isOpened():
        frame_id += 1
        print(frame_id)
        ret, frame = cap.read()
        if frame_id % 5 != 0:
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
                        "push_time": datetime.now().strftime("%d/%m/%y %H:%M:%S"),
                        "video_url": video_url,
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
        kafka_producer.send("emagic.test_pc", json.dumps(message).encode("utf-8"))
        # draw polygon to frame
        for polygon in polygons:
            for i in range(len(polygon[0])):
                cv2.line(
                    frame,
                    tuple(polygon[0][i]),
                    tuple(polygon[0][(i + 1) % len(polygon[0])]),
                    (0, 255, 0),
                    2,
                )
        cv2.imshow("output", frame)
        # cv2.imshow("output", frame)
        if cv2.waitKey(1) == ord("q"):
            break
