# import cv2
# import math
# import argparse
# from ultralytics import YOLO
# import supervision as sv
# import time
# import json
# from draw import draw_bb
# from minio_cl import minio_client
# from kafka import KafkaProducer

# kafka_broker = '47.128.81.230:8003'
# storage_bucket = 'emagic-event'
# kafka_producer = KafkaProducer(bootstrap_servers=['47.128.81.230:8003'],
#                                request_timeout_ms=5000,
#                                max_block_ms=5000)

# caches = {}
# violations = {}
# frame_ids = []
# bboxs = []


# def iou(box1, box2):
#     """
#     Calculate intersection over union
#     :param box1: a[0], a[1], a[2], a[3] <-> left, top, right, bottom
#     :param box2: b[0], b[1], b[2], b[3] <-> left, top, right, bottom
#     """
#     w_intersect = max(0, (min(box1[2], box2[2]) - max(box1[0], box2[0])))
#     h_intersect = max(0, (min(box1[3], box2[3]) - max(box1[1], box2[1])))
#     s_intersect = w_intersect * h_intersect
#     s_a = (box1[2] - box1[0]) * (box1[3] - box1[1])
#     s_b = (box2[2] - box2[0]) * (box2[3] - box2[1])
#     return float(s_intersect) / (s_a + s_b - s_intersect)


# def is_point_inside_polygon(point, pol):
#     return pol.contains(point)


# def compute_distance(p1, p2):
#     x1, y1 = p1
#     x2, y2 = p2
#     return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


# def get_center_point(box):
#     x1, y1, x2, y2 = box
#     return (x1 + x2) / 2, (y1 + y2) / 2


# def check_not_moving(box1, box2):
#     iou_score = iou(box1, box2)
#     if iou_score > 0.8:
#         return True
#     p1 = get_center_point(box1)
#     p2 = get_center_point(box2)
#     center_distance = compute_distance(p1, p2)
#     box_width = box1[2] - box1[0]
#     if center_distance / box_width < 0.05:
#         return True
#     return False


# def checker(message):
#     tracks = message['detections']['tracker_id']
#     for i, track in enumerate(tracks):
#         if message['detections']['class_name'][i] != 'person':
#             continue
#         else:
#             if track not in caches:
#                 caches[track] = {}
#                 caches[track]['frame_ids'] = [message['frame_id']]
#                 caches[track]['bboxes'] = [message['detections']['xyxy'][i]]
#                 caches[track]['first_standing_frame_id'] = message['frame_id']
#             else:
#                 caches[track]['frame_ids'].append(message['frame_id'])
#                 caches[track]['bboxes'].append(message['detections']['xyxy'][i])
#                 cur_index = len(caches[track]['bboxes']) - 1
#                 if check_not_moving(caches[track]['bboxes'][cur_index-1], caches[track]['bboxes'][cur_index]):
#                     if (message['frame_id'] - caches[track]['first_standing_frame_id']) > 30:
#                         print(f"Detect track {track} is violent because inactive more than 30 frame")
#                         violations[track] = caches[track]
#                 else:
#                     caches[track]['first_standing_frame_id'] = message['frame_id']


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(prog='RainScale')
#     parser.add_argument("--model", type=str, required=True)
#     parser.add_argument("--video", type=str, required=True)
#     parser.add_argument("--feature", type=str, default='VEH01')
#     args = parser.parse_args()

#     frame_id = 0
#     tracker = sv.ByteTrack()
#     box_annotator = sv.BoundingBoxAnnotator()
#     label_annotator = sv.LabelAnnotator()
#     cap = cv2.VideoCapture(args.video)
#     yolo = YOLO(args.model)

#     results = []
#     size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
#             int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))

#     while cap.isOpened():
#         frame_id += 1
#         ret, frame = cap.read()
#         if not ret:
#             break

#         h, w, _ = frame.shape
#         results = yolo(frame, verbose=False)[0]
#         detections = sv.Detections.from_ultralytics(results)
#         detections = tracker.update_with_detections(detections)
#         frame = box_annotator.annotate(frame.copy(), detections=detections)

#         labels = [
#             f"#{tracker_id} {results.names[class_id]}"
#             for class_id, tracker_id
#             in zip(detections.class_id, detections.tracker_id)
#         ]
#         # print(labels)
#         if len(detections) == len(labels):
#             frame = label_annotator.annotate(
#                 frame, detections=detections, labels=labels
#             )
#         detections = {
#             "xyxy": detections.xyxy.tolist(),
#             "confidence": detections.confidence.tolist(),
#             "tracker_id": detections.tracker_id.tolist(),
#             "class_id": detections.class_id.tolist(),
#             "class_name": detections.data["class_name"].tolist()
#         }
#         msg = {
#             "frame_id": frame_id,
#             "detections": detections
#         }
#         checker(msg)

#         ## display output
#         cv2.imshow('output', frame)
#         if cv2.waitKey(1) == ord('q'):
#             break

#     frame_id = 0
#     f_name = f'{str(time.time())}_HM07.mp4'
#     img_name = f'{str(time.time())}_HM07.jpg'
#     video = cv2.VideoWriter(f_name, cv2.VideoWriter_fourcc(*'avc1'), 25, size)

#     cap = cv2.VideoCapture(args.video)
#     while cap.isOpened():
#         is_saved_img = False
#         frame_id += 1
#         ret, frame = cap.read()
#         if not ret:
#             break
#         for tracker_id in violations:
#             for i, f_id in enumerate(caches[tracker_id]['frame_ids']):
#                 if frame_id == f_id:
#                     bbox = caches[tracker_id]['bboxes'][i]
#                     x1, y1, x2, y2 = bbox
#                     frame = draw_bb(frame, bbox, color=(0, 0, 255), label='HM07')
#                     if not is_saved_img:
#                         cv2.imwrite(img_name, frame)
#                         is_saved_img = True
#         video.write(frame)
#     cv2.destroyAllWindows()
#     video.release()
#     time.sleep(5)
#     img_url = minio_client.upload_file(storage_bucket, img_name, img_name)
#     video_url = minio_client.upload_file(storage_bucket, f_name, f_name)
#     data = {
#         'camera_id': 7197878761902219,
#         'event_type': 'HM05',
#         'event_id': str(time.time()),
#         'status': 'OPEN',
#         'image_url': img_url,
#         'video_url': video_url,
#         'event_time': str(time.time()),
#     }
#     print('Sending data to kafka...')
#     kafka_event_topic = 'emagic.events'
#     print(kafka_producer.send(kafka_event_topic, value=json.dumps(data).encode("utf-8")))
#     kafka_producer.flush()
#     print('Done!')
