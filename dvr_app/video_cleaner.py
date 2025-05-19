import shutil
from datetime import datetime
import os
import time
import logging
import glob

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
                    handlers=[logging.StreamHandler()])  # Logs to stdout


def ts_to_datetime(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def delete_old_files(directory, hours):
    logging.info(f"Checking for files older than {hours} hours in {directory}...")
    time_threshold = time.time() - (hours * 3600)

    # Walk through the directory and its subdirectories
    for root, dirs, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)

            # Check if it's a file (not a directory)
            if os.path.isfile(file_path):
                # Get the file's creation time
                modification_time = os.path.getmtime(file_path)

                # If the file is older than the threshold, delete it
                if modification_time < time_threshold:
                    os.remove(file_path)
                    logging.info(f"Deleted: {file_path}")


def move_folders_based_on_time(source_dir: str, des_dir: str, hours_threshold: int):
    current_time = time.time()

    dir_paths = glob.glob(os.path.join(source_dir, "*/*/*"))
    for dir_path in dir_paths:
        if os.path.isdir(dir_path):
            modified_time = os.path.getmtime(dir_path)

            time_difference = current_time - modified_time

            threshold_in_seconds = hours_threshold * 3600

            if time_difference > threshold_in_seconds:
                relative_path = os.path.relpath(dir_path, source_dir)
                new_path = os.path.join(des_dir, relative_path)

                os.makedirs(os.path.dirname(new_path), exist_ok=True)

                if os.path.exists(new_path):  # If the folder already exists in the destination folder
                    shutil.rmtree(new_path)
                    logging.info(f"Deleted existing folder: {new_path} because it's duplicate")
                shutil.move(dir_path, new_path)
                logging.info(f"Moved {dir_path} to {new_path}")


class FileManager:
    def __init__(self, interval=30):
        self.jobs = []
        self.interval = interval

    def add_job(self, job, *args):
        self.jobs.append((job, args))

    def run(self):
        while True:
            for job, args in self.jobs:
                try:
                    job(*args)
                except Exception as e:
                    logging.error(f"Error running job: {job.__name__} - {e}")
                    logging.warning(f"Skipping job: {job.__name__}")
            time.sleep(self.interval)



if __name__ == "__main__":
    logging.info("***** Video Cleaner Service ******")
    clean_time = int(os.getenv("CLEAN_TIME", default=24))
    clean_folder = os.getenv("CLEAN_FOLDER", default="/usr/dvr_videos")

    move_file_time = int(os.getenv("MOVE_FILE_TIME", default=24))
    source_move_folder = os.getenv("SOURCE_MOVE_FOLDER", default="/source_data")
    des_move_folder = os.getenv("DES_MOVE_FOLDER", default="/des_data")

    file_manager = FileManager()
    file_manager.add_job(delete_old_files, clean_folder, clean_time)
    file_manager.add_job(move_folders_based_on_time, source_move_folder, des_move_folder, move_file_time)

    file_manager.run()
