import os
import sys
import cv2
import numpy as np
from ultralytics import YOLO
from os import path as osp

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cloud_app.internal.controller.hm08.track import SimpleTracker
from cloud_app.internal.controller.hm08.detection import Detection
from cloud_app.internal.pkg.box import draw_bb_hm08

# 
VIDEO_PATH = "/home/huannd/phuc_long_src/input_video/video_input.mp4"
MODEL_PATH = "/home/huannd/phuc_long_src/yolo11m.pt"
SAVE_VIDEO_DIR = "/home/huannd/phuc_long_src/output_video"

FPS = 25
IDLE_SECONDS = 120
FRAME_THRESHOLD = FPS * IDLE_SECONDS
CENTER_THRESHOLD = 100
TOLERANCE_FRAMES = 10

# MODEL & TRACKER 
yolo = YOLO(MODEL_PATH)
tracker = SimpleTracker(distance_threshold=90, iou_threshold=0.2, max_miss=60)

#  UTILS 
def get_center(bbox):
    x1, y1, x2, y2 = bbox
    return [(x1 + x2) // 2, (y1 + y2) // 2]

def is_stationary(center1, center2, threshold=CENTER_THRESHOLD):
    return abs(center1[0] - center2[0]) <= threshold and abs(center1[1] - center2[1]) <= threshold

def compute_iou_bbox(box1, box2):
    xA = max(box1[0], box2[0])
    yA = max(box1[1], box2[1])
    xB = min(box1[2], box2[2])
    yB = min(box1[3], box2[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = max(1, (box1[2] - box1[0]) * (box1[3] - box1[1]))
    boxBArea = max(1, (box2[2] - box2[0]) * (box2[3] - box2[1]))
    return interArea / (boxAArea + boxBArea - interArea + 1e-5)

def nms_numpy(boxes, scores, iou_threshold=0.5):
    if len(boxes) == 0:
        return []
    boxes = np.array(boxes)
    scores = np.array(scores)
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter_w = np.maximum(0.0, xx2 - xx1 + 1)
        inter_h = np.maximum(0.0, yy2 - yy1 + 1)
        inter_area = inter_w * inter_h
        union_area = areas[i] + areas[order[1:]] - inter_area
        iou = inter_area / (union_area + 1e-6)
        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]
    return keep

# MAIN 
def process_video(video_fp):
    os.makedirs(SAVE_VIDEO_DIR, exist_ok=True)
    cap = cv2.VideoCapture(video_fp)
    if not cap.isOpened():
        print(f"khong mo dc video: {video_fp}")
        return

    base = osp.splitext(osp.basename(video_fp))[0]
    out_path = osp.join(SAVE_VIDEO_DIR, f"{base}_output.mp4")
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (w, h))

    frame_id = 0
    idle_ids = set()
    idle_state = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_id += 1

        results = yolo(frame, classes=[0])[0]
        raw_boxes = results.boxes.xyxy.cpu().numpy()
        raw_scores = results.boxes.conf.cpu().numpy()

        filtered = [(b, s) for b, s in zip(raw_boxes, raw_scores) if s > 0.5]
        boxes = []
        if filtered:
            bboxes, scores = zip(*filtered)
            keep = nms_numpy(bboxes, scores, iou_threshold=0.5)
            boxes = [list(map(int, bboxes[i])) for i in keep]

        tracks = tracker.update(boxes, frame_id)

        new_tracks = []
        for tid, bbox in tracks:
            center = get_center(bbox)
            merged_id = tid

            for old_id, state in idle_state.items():
                if state["alerted"]: continue
                if state["start_frame"] is None: continue
                if old_id == tid: continue
                if frame_id - state.get("last_seen", 0) < 5:
                    if is_stationary(center, state["base_center"], threshold=70):
                        if "base_center_box" in state:
                            iou = compute_iou_bbox(bbox, state["base_center_box"])
                            if iou < 0.3:
                                continue
                        idle_duration = frame_id - state["start_frame"]
                        if idle_duration > FRAME_THRESHOLD // 2:
                            continue
                        print(f" Gộp ID mới {tid} → ID cũ {old_id} (frame {frame_id})")
                        merged_id = old_id
                        break

            new_tracks.append((merged_id, bbox))

        for tid, bbox in new_tracks:
            center = get_center(bbox)

            if tid not in idle_state:
                idle_state[tid] = {
                    "base_center": center,
                    "base_center_box": bbox,
                    "miss": 0,
                    "start_frame": None,
                    "alerted": False
                }

            state = idle_state[tid]
            if is_stationary(center, state["base_center"], threshold=CENTER_THRESHOLD):
                state["miss"] = 0
                if state["start_frame"] is None:
                    state["start_frame"] = frame_id
            else:
                state["miss"] += 1
                if state["miss"] > TOLERANCE_FRAMES:
                    state["base_center"] = center
                    state["base_center_box"] = bbox
                    state["start_frame"] = None
                    state["miss"] = 0
                    state["alerted"] = False

            if state["start_frame"] is not None:
                idle_duration = frame_id - state["start_frame"]
                if idle_duration >= FRAME_THRESHOLD and not state["alerted"]:
                    print(f"[ALERT] ID {tid} đứng/ngồi yên ≥ {IDLE_SECONDS}s tại frame {state['start_frame']}")
                    idle_ids.add(tid)
                    state["alerted"] = True

            state["last_seen"] = frame_id
            color = (0, 0, 255) if tid in idle_ids else (0, 255, 0)
            draw_bb_hm08(frame, bbox, color, f"ID{tid}")

        if idle_ids:
            cv2.putText(frame, "ALERT: ≥ 60s", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

        writer.write(frame)

    cap.release()
    writer.release()
    print(f"[✔] Output saved: {out_path}")

#  RUN 
if __name__ == "__main__":
    process_video(VIDEO_PATH)
