import time
from abc import ABC



class BaseEvent(ABC):
    def __init__(
        self,
        name: str,
        detections: list,
        event_conf: float,
        camera_id: str,
        frame_id: int,
        tenant_id: str,
        area_name: str,
        push_time: float | None = None,
    ):
        self.name = name
        if detections and not isinstance(detections[0], dict):
            detections = [det.to_dict() for det in detections]
        self.detections = detections
        self.event_conf = event_conf
        self.camera_id = camera_id
        self.push_time = push_time if push_time else time.time()
        self.frame_id = frame_id
        self.tenant_id = tenant_id
        self.area_name = area_name

    def to_dict(self):
        return {
            "name": self.name,
            "detections": self.detections,
            "event_conf": self.event_conf,
            "camera_id": self.camera_id,
            "push_time": self.push_time,
            "frame_id": self.frame_id,
            "tenant_id": self.tenant_id,
            "area_name": self.area_name,
        }

    @classmethod
    def from_dict(cls, dict_msg):
        return cls(
            name=dict_msg["name"],
            detections=dict_msg["detections"],
            event_conf=dict_msg["event_conf"],
            camera_id=dict_msg["camera_id"],
            push_time=dict_msg["push_time"],
            frame_id=dict_msg["frame_id"],
            tenant_id=dict_msg.get("tenant_id", "0"),
            area_name=dict_msg.get("area_name", "default"),
        )
