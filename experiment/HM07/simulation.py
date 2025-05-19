import os
import cv2
import sys
import json
import argparse
import supervision as sv
from ultralytics import YOLO
from datetime import datetime
from os import path as osp

sys.path.append("../../")
from cloud_app.internal.controller.hm07 import Camera, Track, Detection
from cloud_app.internal.pkg.box import draw_bb, draw_box_simple

res_viz = {}
import cv2
import numpy as np

def merge_videos_and_draw_boxes(save_path, detections, save_raw_video_dir):
    # Tạo cấu trúc lưu thông tin từng video
    # print("merge_videos_and_draw_boxes...")
    videos_info = {}
    for det in detections:
        video_url = det.video_url
        if video_url not in videos_info:
            videos_info[video_url] = {
                'bboxes': [det.bbox],
                'frames_id': [det.frame_id],
                'classes_name': [det.class_name],
                'confidences': [det.confidence]
            }
        else:
            videos_info[video_url]['bboxes'].append(det.bbox)
            videos_info[video_url]['frames_id'].append(det.frame_id)
            videos_info[video_url]['classes_name'].append(det.class_name)
            videos_info[video_url]['confidences'].append(det.confidence)
    # print(videos_info)

    name_save = "HM07"
    all_frame_ids = []
    for video_url in videos_info:
        all_frame_ids.extend(videos_info[video_url]['frames_id'])
        video_name = osp.basename(video_url)
        name_save += "_" + video_name[:-4]

    name_save += ".mp4"
    save_path = osp.join(save_path, name_save)
    # Khởi tạo VideoWriter cho video đầu ra
    output_fps = 25
    output_duration = 10  # Video đầu ra sẽ tua nhanh trong 10 giây
    total_frames = output_fps * output_duration
    
    output_writer = None
    video_height = None
    video_width = None
    total_frames_processed = 0
    
    frame_step = max(1, len(all_frame_ids) // total_frames)  # Bỏ bớt frame nếu cần
    count_fram_id = 0

    for video_url in videos_info:
        os.system(f"cp {video_url} {save_raw_video_dir}")
        cap = cv2.VideoCapture(video_url)

        if not cap.isOpened():
            print(f"Không mở được video {video_url}")
            continue

        # Lấy kích thước video và khởi tạo output video writer lần đầu
        video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        if output_writer is None:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # codec video
            output_writer = cv2.VideoWriter(save_path, fourcc, output_fps, (video_width, video_height))
        frame_idx = 0  # Khởi tạo frame index trong video
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Kiểm tra nếu frame nằm trong các frame cần giữ lại
            if frame_idx in videos_info[video_url]['frames_id']:
                if count_fram_id % frame_step == 0 or frame_idx == videos_info[video_url]['frames_id'][-1]:
                    # Lấy các bounding box và class_name tương ứng
                    bbox_idx = videos_info[video_url]['frames_id'].index(frame_idx)
                    bbox = videos_info[video_url]['bboxes'][bbox_idx]
                    class_name = videos_info[video_url]['classes_name'][bbox_idx] + "_" + str(videos_info[video_url]['confidences'][bbox_idx])[:5]

                    x1, y1, x2, y2 = bbox
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, class_name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                    output_writer.write(frame)
                    total_frames_processed += 1
                count_fram_id += 1
            frame_idx += 1
        cap.release()

    if output_writer is not None:
        output_writer.release()
    print(f"Video output đã được lưu tại {save_path}")


def process_video(video_path, yolo, cam_id, save_frame_dir, save_video_dir, camera, config, save_raw_video_dir):
    frame_id = 0
    cap = cv2.VideoCapture(video_path)
    size = (
        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    )
    saved_video = None
    print("Input video url: {}".format(video_path))
    video_name = os.path.basename(video_path).split(".")[0]
    frame_list = []
    flag_to_save_video = 0 #always save video
    while cap.isOpened():
        frame_id += 1
        ret, frame = cap.read()
        if frame_id % 5 != 0:
            continue
        if not ret:
            break
        h, w, _ = frame.shape
        results = yolo(frame, verbose=False)[0]
        detections = sv.Detections.from_ultralytics(results)

        detection_data = []
        xyxy_list = detections.xyxy.tolist()
        confidence_scores = detections.confidence.tolist()
        class_ids = detections.class_id.tolist()
        class_names = detections.data["class_name"].tolist()
        # print("class_names: ", class_names)
        for i in range(len(xyxy_list)):
            try:
                detection_data.append(
                    {
                        "xyxy": xyxy_list[i],
                        "confidence": confidence_scores[i],
                        "class_id": class_ids[i],
                        "class_name": class_names[i],
                        "frame_id": frame_id,
                        "cam_id": cam_id,
                        "detect_time": frame_id,
                        "push_time": datetime.now().strftime(
                            "%d/%m/%y %H:%M:%S"
                        ),
                        "video_url": video_path,
                    }
                )
            except Exception as e:
                print(e)
        detections = [
            Detection(
                msg=det, frame_id=frame_id, cam_id=cam_id, video_url=video_path
            )
            for det in detection_data
        ]

        valid_detections = [det for det in detections if det.track_id is not None]
        try:
            display_frame = camera.update_tracks(
                detections=valid_detections, frame_id=frame_id, frame=frame, testing=True
            )
        except ValueError as e:
            print(f"ValueError: {e}")
            continue  # Bỏ qua frame này nếu có lỗi

        event_detections, frame = camera.event_checking(frame_id=frame_id, frame=frame)
        if len(event_detections):
            print(len(event_detections))
            flag_to_save_video = len(frame_list)
            merge_videos_and_draw_boxes(save_video_dir, event_detections, save_raw_video_dir)
    return camera
if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="RainScale")
    parser.add_argument("--model", type=str, required=False, default="/ssd1/thinhnv/mge_ai_cloud/experiment/MHE01/yolov8m.pt")
    parser.add_argument("--video_url", type=str, required=False)
    parser.add_argument("--video_folder", type=str, required=True)
    parser.add_argument("--cam_id", type=str, required=False)
    parser.add_argument(
        "--save_video_dir",
        type=str,
        default="./linfox_DCBD-192_168_253_33_conf_0.5_limit_time_300_merge_video_distance_threshold_0.15_moving_saved",
    )
    config = {"max_miss":10,"limit_time":300, "cam_resolution":[1920,1080],"target_class":"person","cam_zones":[],"violent_count":600,"image_height":1080,"image_width":1920}

    args = parser.parse_args()
    cam_id = args.cam_id
    yolo = YOLO(args.model)
    camera = Camera(cam_id=cam_id, config=config)

    camera_id = args.video_folder.split("/")[-1]
    save_frame_dir = f"{args.save_video_dir}/{camera_id}"
    save_video_dir = f"{args.save_video_dir}/{camera_id}"
    save_raw_video_dir = f"{args.save_video_dir}/{camera_id}"
    output_file_path = f"./{args.save_video_dir}/processed_videos.txt"  # File để lưu đường dẫn video đã xử lý
    # os.system(f'rm {output_file_path}')
    # os.system(f'touch {output_file_path}')
    os.makedirs(save_frame_dir, exist_ok=True)
    # os.makedirs(save_video_dir, exist_ok=True)
    # os.makedirs(save_raw_video_dir, exist_ok=True)

    from tqdm import tqdm
    from glob import glob
    
    if args.video_folder:
        video_li_path = glob(os.path.join(args.video_folder, "*.mp4"))
        video_li_path.sort()

        for video_path in tqdm(video_li_path[:]):
            with open(output_file_path, "a") as f:
                f.write(f"{video_path}\n")
            video_name = os.path.basename(video_path)
            if not video_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                continue  # Bỏ qua các tệp không phải video
            process_video(video_path, yolo, cam_id, save_frame_dir, save_video_dir, camera, config, save_raw_video_dir)
            # print(camera)
            # print(camera.tracked_objects)
            # print("Done==================================================")
    # if args.video_url:
        # video_path = args.video_url
        # video_name = os.path.basename(video_path)
        # process_video(video_path, yolo, cam_id, save_frame_dir, save_video_dir, camera, config, save_raw_video_dir)
  