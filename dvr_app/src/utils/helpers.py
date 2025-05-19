import os

def get_video_start_end_datetime(video_url: str, duration: int):
    end_time = float(os.path.getctime(video_url))
    start_time = end_time - duration
    return start_time, end_time