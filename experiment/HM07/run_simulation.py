import os
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from glob import glob

videos_folder_path_all = "/hdd1/dinhcc/live/*"
output_file_path = "./processed_videos.txt"  # File để lưu đường dẫn video đã xử lý

def process_video(video_folder):
    os.system(f"python simulation.py --video_folder {video_folder}")
    with open(output_file_path, "a") as f:
        f.write(f"{video_path}\n")



video_fols = glob(videos_folder_path_all)
# print(video_fols)
with ThreadPoolExecutor(max_workers=8) as executor:  # Bạn có thể điều chỉnh số lượng workers theo số lượng CPU cores
    list(tqdm(executor.map(process_video, video_fols), total=len(video_fols)))

