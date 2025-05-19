import os
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import time
from multiprocessing import Pool
config_map = {
    #"linfox_DCBD-192_168_253_9": {"max_miss": 40, "cam_resolution": [1920, 1080], "target_class": ["person", "forklift", "hand_pallet_jack", "electric_pallet_jack", "reach_truck", "product_package"], "no_walking_zones": [[[1500, 1075], [485, 1057], [786, 345], [1095, 360]]], "violent_count": 5, "speed_threshold": 15}, 
}
videos_folder_path_all = "/hdd1/dinhcc/data_BD/live"
output_file_path = f"/ssd1/dinhcc/mge_ai_cloud/experiment/HM05/processed_videos_BD_300.txt"  # File để lưu đường dẫn video đã xử lý

if os.path.exists(output_file_path):
    os.remove(output_file_path)

os.system(f"touch {output_file_path}")

def process_video(video_file):
    if not video_file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        return  # Bỏ qua các tệp không phải video
    video_path = os.path.join(videos_folder_path, video_file)
    with open(output_file_path, "r") as f:
        processed_videos = f.readlines()
    processed_videos = [v.strip() for v in processed_videos]
    if video_path in processed_videos:
        return
    
    os.system(f"python simulation.py --video_url {video_path}")
    with open(output_file_path, "a") as f:
        f.write(f"{video_path}\n")
for key, val in config_map.items():
    # Tạo đường dẫn đến thư mục video
    videos_folder_path = os.path.join(videos_folder_path_all, key)
    
    # Kiểm tra xem thư mục có tồn tại không
    if not os.path.exists(videos_folder_path):
        print(f"Folder {videos_folder_path} not found.")
        continue
    # Lấy danh sách các tệp video 200 videos in each folder
    video_files = [f for f in os.listdir(videos_folder_path) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]

    video_files = sorted(video_files)[::3]
    
    # Xử lý các video song song với ThreadPoolExecutor
    with Pool(processes=4) as pool:  # Bạn có thể điều chỉnh số lượng processes theo số lượng CPU cores
        list(tqdm(pool.imap(process_video, video_files), total=len(video_files)))