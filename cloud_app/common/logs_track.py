import time
from collections import Counter
from loguru import logger
from datetime import datetime, timedelta, timezone

def logs_infor(self, frame_id: int) -> None:
    current_time = datetime.now(timezone(timedelta(hours=7)))
    formatted_time = current_time.strftime('%d-%m-%Y_%H:%M:%S')
    li_camera_id = []
    li_video_url = []
    for track in self.tracked_objects:
        video_url_track = [det.video_url for det in track.detections]
        li_video_url.extend(video_url_track)
    li_video_url = list(set(li_video_url))
    li_camera_id = [video_url.split('/')[-2] for video_url in li_video_url]
    number_of_videos = len(li_camera_id)
    count_videos = Counter(li_camera_id)
    li_camera_id = list(set(li_camera_id))
    if number_of_videos % 2 == 0 and frame_id < 10:
        logger.info(f"Event checking: {formatted_time}")
        logger.info(f"List of camera IDs and number of videos in each camera ID")
        for camera_id in li_camera_id:
            logger.info(f">>>>>>>>>> {camera_id}: {count_videos[camera_id]} videos")
        logger.info(f"Length of tracked_objects: {len(self.tracked_objects)}")
        logger.info(f"===========================================================")

def event_logs(track):
    logger.info(f"======================= EVENT ACCEPTED =======================")
    logger.info(f"Track_id {track.track_id}")
    logger.info(f"Video_url: {track.detections[0].video_url}")
    logger.info(f"Video_url: {track.detections[-1].video_url}")
    logger.info(f"Event Accepted")
    logger.info(f"===================== END EVENT ACCEPTED =====================")