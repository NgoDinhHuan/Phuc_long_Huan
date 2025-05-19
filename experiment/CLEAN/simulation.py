import os
import cv2
import sys
import json
import argparse
import supervision as sv
from ultralytics import YOLO
from datetime import datetime
sys.path.append("../../")
from cloud_app.internal.controller.CLEAN import Camera, Track, Detection
from cloud_app.internal.pkg.box import draw_bb, draw_box_simple
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

config_map = {
    "linfox_DCBD-192_168_253_9": {"max_miss": 40, "cam_resolution": [1920, 1080], "confidence_threshold": 0.7, "target_class": ["person", "forklift", "hand_pallet_jack", "electric_pallet_jack", "reach_truck", "product_package"], "no_walking_zones": [[[1500, 1075], [485, 1057], [786, 345], [1095, 360]]], "mhe_intersect_area_threshold": 0.3, "product_intersect_area_threshold": 0.3, "person_moved_distance_threshold": 3, "number_frame_intersect_mhe_threshold": 5, "number_frame_intersect_product_threshold": 5, "speed_threshold": 15}, 
}

res_viz = {}
def process_video(video_path, yolo, cam_id, save_frame_dir, save_video_dir, camera, config, save_raw_video_dir):
    frame_id = 0
    cap = cv2.VideoCapture(video_path)
    size = (
        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    )
    saved_video = None
    # saved_video = cv2.VideoWriter(
    #                 f"{save_video_dir}/{os.path.basename(video_path)}",
    #                 cv2.VideoWriter_fourcc(*"MP4V"),
    #                 25,
    #                 size,
    #             )
    print("Input video url: {}".format(video_path))
    video_name = os.path.basename(video_path).split(".")[0]
    frame_list = []
    flag_to_save_video = 0
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
        # print(len(xyxy_list), len(confidence_scores), len(class_ids), len(class_names))
        # print("class_names: ", class_names)
        for i in range(len(xyxy_list)):
            try:
                detection_data.append(
                    {
                        "xyxy": xyxy_list[i],
                        "confidence": confidence_scores[i],
                        "class_id": class_ids[i],
                        "class_name": class_names[i].lower().replace(" ", "_"),
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
        # for det in valid_detections:
        #     print(f"Track ID: {det.track_id}, Class: {det.class_name}, Confidence: {det.confidence}")
        # Kiểm tra số lượng nhãn và số lượng phát hiện
        try:
            display_frame = camera.update_tracks(
                detections=valid_detections, frame_id=frame_id, frame=frame, testing=True
            )
        except ValueError as e:
            print(f"ValueError: {e}")
            continue  # Bỏ qua frame này nếu có lỗi
        if display_frame is not None:
            frame = display_frame
            # cv2.imwrite(f"{save_frame_dir}/{frame_id}.jpg", display_frame)
        event_detections, frame = camera.event_checking(frame_id=frame_id, frame=frame)
        # print(f"Number detection of event: {len(event_detections)}")
        if len(event_detections):
            print(len(event_detections))
            flag_to_save_video = len(frame_list)
            # res_viz[frame_id] = event_detections
            # print("Saved frame to {}.jpg".format(save_frame_dir, frame_id))
            # msg = camera.create_event(
            #     event_name="MHE04",
            #     detections=event_detections,
            #     frame_id=frame_id,
            # )
            # msg["frame_id"] = frame_id
            # print(
            #     "Send Kafka message to {} with track_id {}".format(
            #         "MHE04",
            #         event_detections[0].track_id,
            #     )
            # )
            # kafka_producer.send(
            #     cfg.kafka_evidence_topic, json.dumps(msg).encode("utf-8")
            # )
            for eds in event_detections:
                for ed in eds:
                    x1, y1, x2, y2 = ed.bbox
                    print(f"Drawed in {video_path}:",x1, y1, x2, y2)
                    frame = cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    # frame = cv2.putText(
                    #     frame,
                    #     f"HM05",
                    #     (x1, y1 - 10),
                    #     cv2.FONT_HERSHEY_SIMPLEX,
                    #     1,
                    #     (0, 0, 255),
                    #     2,
                    #     cv2.LINE_AA,
                    # )
            
            cam_name = video_path.split("/")[-2]
            cv2.imwrite(f"{save_frame_dir}/{cam_name}_{video_name}_{frame_id}.jpg", frame)
            if saved_video is None:
                saved_video = cv2.VideoWriter(
                    f"{save_video_dir}/{os.path.basename(video_path)}",
                    cv2.VideoWriter_fourcc(*"MP4V"),
                    25,
                    size,
                )
            if saved_video:
                for i in range(5):
                    frame_list.append(frame)
                    
        # if saved_video:
            # saved_video.write(frame)
        frame_list.append(frame)
    if flag_to_save_video and saved_video:
        print("Saved video to {}".format(save_video_dir))
        os.system(f"cp {video_path} {save_raw_video_dir}")
        start_frame = max(0,flag_to_save_video - 75)
        end_frame = min(flag_to_save_video + 175, len(frame_list))
        print(start_frame, end_frame, '---------------->')
        print("len frame list:",len(frame_list))
        for frame in frame_list[start_frame: end_frame]:
            saved_video.write(frame)
        
        cap.release()
        saved_video.release()
if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="RainScale")
    parser.add_argument("--model", type=str, required=False, default="/ssd1/dinhcc/best.engine")
    # parser.add_argument("--videos_folder_path", type=str, required=False, default="/ssd1/thinhnv/Yedda/mge_ai_cloud/experiment/MHE01/videos_test")
    parser.add_argument("--video_url", type=str, required=True)
    parser.add_argument("--cam_id", type=str, required=False)
    parser.add_argument(
        "--save_video_dir",
        type=str,
        default="/hdd1/dinhcc/inferences/hm05_fix_product_package",
    )
    # default_video_url = "/ssd1/thinhnv/Yedda/mge_ai_cloud/experiment/MHE01/1727140219786.mp4"
    # default_videos_folder_path = "/ssd1/thinhnv/Yedda/mge_ai_cloud/experiment/MHE01/videos_test/linfox_DCBD-192_168_253_9/"
    args = parser.parse_args()
    video_path = args.video_url
    cam_name = video_path.split("/")[-2]
    config = config_map[cam_name]
    cam_id = args.cam_id
    yolo = YOLO(args.model)
    camera = Camera(cam_id=cam_id, config=config)
    save_frame_dir = f"{args.save_video_dir}/event_frames"
    save_video_dir = f"{args.save_video_dir}/event_videos"
    save_raw_video_dir = f"{args.save_video_dir}/{cam_name}/raw_videos"
    os.makedirs(save_frame_dir, exist_ok=True)
    os.makedirs(save_video_dir, exist_ok=True)
    os.makedirs(save_raw_video_dir, exist_ok=True)
    
    # from tqdm import tqdm
    # # # if args.videos_folder_path:
    # videos_folder_path = default_videos_folder_path
    # for video_file in tqdm(os.listdir(videos_folder_path)):
    #     video_path = os.path.join(videos_folder_path, video_file)
    #     video_name = os.path.basename(video_path)
    #     save_frame_dir = f"{args.save_video_dir}/frames"
    #     save_video_dir = f"{args.save_video_dir}/videos"
    #     os.makedirs(save_frame_dir, exist_ok=True)
    #     os.makedirs(save_video_dir, exist_ok=True)
    #     if not video_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
    #         continue  # Bỏ qua các tệp không phải video
    #     process_video(video_path, yolo, cam_id, save_frame_dir, save_video_dir, camera, config)
    # elif args.video_url:
    if  args.video_url:
        video_path = args.video_url
        video_name = os.path.basename(video_path)
        # save_frame_dir = f"{args.save_video_dir}/frames"
        # save_video_dir = f"{args.save_video_dir}/videos"
        # os.makedirs(save_frame_dir, exist_ok=True)
        # os.makedirs(save_video_dir, exist_ok=True)
        process_video(video_path, yolo, cam_id, save_frame_dir, save_video_dir, camera, config, save_raw_video_dir)
    # elif default_video_url:
    # process_video(default_video_url, yolo, cam_id, save_frame_dir, save_video_dir, camera, config)
    # elif default_videos_folder_path:
    #     for video_file in os.listdir(default_videos_folder_path):
    #         video_path = os.path.join(default_videos_folder_path, video_file)
    #         if not video_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
    #             continue  # Bỏ qua các tệp không phải video
    #         process_video(video_path, yolo, cam_id, save_frame_dir, save_video_dir, camera, config)
    # else:
    #     print("Either --videos_folder_path or --video_url must be provided.")
#python simulation.py --model /ssd1/dinhcc/inferences/MHE04/forklift_person.pt --video_url /hdd1/dinhcc/inferences/MHE03/mhe03_test.mp4