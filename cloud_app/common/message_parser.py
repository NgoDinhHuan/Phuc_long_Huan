import time
from typing import List, Dict, Any
from urllib.parse import urlparse

class MessageParser:
    cam_id: str
    frame_id: int
    detections: List[Any]
    video_url: str
    push_time: float
    extra_information: Dict[str, Any]
    is_ok: bool = False

    DEFAULT_EXTRA_INFORMATION = {
        "camera_key": "",
        "features": [],
        "models": [],
        "status": "new",  # status of config
        "start_time": time.time(), # timestamp in seconds
        "end_time": time.time(),  # timestamp in seconds
        "tenant_id": "",
        "tenant_name": "",
        "area_name": "",
    }

    def __init__(self, message: Dict[str, Any]):
        self.cam_id = message.get("cam_id", "")
        self.frame_id = message.get("frame_id", 0)
        self.detections = message.get("detections", [])
        self.video_url = urlparse(message.get("video_url", "")).path
        self.push_time = message.get("push_time", time.time())
        self.extra_information = message.get("extra_information", self.DEFAULT_EXTRA_INFORMATION.copy())
        self.is_ok = self.check_validity()

    def check_validity(self):
        if (
            self.cam_id and
            isinstance(self.frame_id, int) and self.frame_id >= 0 and
            isinstance(self.detections, list) and
            self.video_url and
            self.extra_information_valid()
        ):
            return True
        return False

    def extra_information_valid(self) -> bool:
        required_fields = ["camera_key", "status", "start_time", "end_time"]
        for field in required_fields:
            if field not in self.extra_information or not self.extra_information[field]:
                return False
        return True

    @classmethod
    def parse_message(cls, message: Dict[str, Any]):
        return cls(message)

    def __str__(self):
        return f"Receive message: cam_id: {self.cam_id}, frame_id: {self.frame_id}, video_url: {self.video_url}, push_time: {self.push_time}"
