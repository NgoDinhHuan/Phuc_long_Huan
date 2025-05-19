import asyncio
import os
import time
import requests

from loguru import logger
from datetime import datetime, timezone


def remove_files(files: list):
    for file in files:
        if os.path.isfile(file):
            os.remove(file)
        else:
            logger.error(f"File not found {file}")


def delete_folder_with_exclusions(folder_path, exclusions=None):
    """
    remove all files and sub-folders in a folder except for the exclusions

    :param folder_path: The path to the folder to be deleted.
    :param exclusions: A list of paths to be excluded from deletion.
    """
    if exclusions is None:
        exclusions = []
    for root, dirs, files in os.walk(folder_path, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            if file_path not in exclusions:
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
            else:
                logger.info(f"File {file_path} is excluded, not deleted.")

        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if dir_path not in exclusions:
                os.rmdir(dir_path)
                logger.info(f"Deleted folder: {dir_path}")
            else:
                logger.info(f"Folder {dir_path} is excluded, not deleted.")

    if folder_path not in exclusions:
        os.rmdir(folder_path)
        logger.info(f"Deleted folder: {folder_path}")
    else:
        logger.info(f"Folder {folder_path} is excluded, not deleted.")


def init_save_paths(cam_key: str,
                    event_name: str,
                    detect_time: int|float,
                    tenant_id: str,
                    area_name: str,
                    base_folder: str,
                    event_id: str):

    current_time = convert_timestamp_to_datetime(time.time(), format_time='%d_%H-%M-%S')
    detect_datetime = convert_timestamp_to_datetime(detect_time, format_time='%d_%H-%M-%S')
    # Init save paths
    base_name = "event_{}_now_{}".format(detect_datetime, current_time)
    base_dir = "{}/{}/{}/{}".format(base_folder, event_name, cam_key, event_id)
    base_dir = base_dir.replace(" ", "_")

    os.makedirs(base_dir, exist_ok=True)

    thumbnail_path = "{}/{}_thumbnail.jpg".format(base_dir, base_name)
    video_path = "{}/{}.mp4".format(base_dir, base_name)
    img_path = "{}/{}.jpg".format(base_dir, base_name)
    crop_video_path = "{}/{}_crop.mp4".format(base_dir, base_name)

    # Init minio paths
    current_date = convert_timestamp_to_datetime(time.time(), format_time='%d-%m-%Y')

    minio_thumbnail_path = "{}/{}/{}/{}/{}".format(
        tenant_id, area_name, current_date, event_name, thumbnail_path.split("/")[-1]
    )
    minio_video_path = "{}/{}/{}/{}/{}".format(
        tenant_id, area_name, current_date, event_name, video_path.split("/")[-1]
    )
    minio_img_path = "{}/{}/{}/{}/{}".format(
        tenant_id, area_name, current_date, event_name, img_path.split("/")[-1]
    )

    return (thumbnail_path, video_path, img_path, crop_video_path,
            minio_thumbnail_path, minio_video_path, minio_img_path, base_dir)


def convert_timestamp_to_datetime(timestamp: float|int, format_time: str = "%Y-%m-%d %H:%M:%S.%f"):
    dt_object = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    formatted_time = dt_object.strftime(format_time)

    return formatted_time


async def check_exist_and_wait_for_files(file_path_list: list, timeout: int = 10):
    """
    Check if the file exists and wait for it to be created
    :param file_path_list: The path to the file
    :param timeout: The time to wait for the file to be created
    :return: True if the file exists, False otherwise
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if all([os.path.exists(file_path) for file_path in file_path_list]):
            return True
        await asyncio.sleep(0.5)
    else:
        for file_path in file_path_list:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
        return False

def post_to_event_collector(event_collector_url: str, event_type: str):
    try:
        response = requests.post(event_collector_url, json={"event_type": event_type})
        logger.info(f"Sent event to collector url: {event_collector_url}. Response: {response.json()}")
        return response.json()
    except Exception:
        logger.error(f"Error: Failed to connect to event collector.")
        return None