from cloud_app.internal.controller.base.track import BaseTrack
from cloud_app.internal.controller.hm05.detection import Detection
from collections import deque

class Track(BaseTrack):
    violent_count = None

    def __init__(
        self,
        track_id: int,
        class_id: int,
        class_name: str,
        violent_count: int = -1,
        detections: list[Detection] = None,
        first_violent_bbox=0,
        max_distane=0,
        number_of_frames_operating_forklift=0,
        number_of_frames_intersect_product=0,
        confidence_list= deque(maxlen=100),
    ):
        super().__init__(
            track_id=track_id,
            class_id=class_id,
            class_name=class_name,
            detections=detections,
            violent_count=violent_count,
        )
        self.first_violent_bbox = first_violent_bbox
        self.max_distane = max_distane
        self.number_of_frames_operating_forklift = number_of_frames_operating_forklift
        self.number_of_frames_intersect_product = number_of_frames_intersect_product
        self.confidence_list = confidence_list

    def update_detection(self, detection: Detection):
        super().update_detection(detection)

    def add_missed_frame(self, frame_id: int):
        super().add_missed_frame(frame_id)

    def reset_miss(self):
        super().reset_miss()

    @staticmethod
    def create(detection: Detection, track_id: int, frame_id: int):
        return Track(
            class_id=detection.class_id,
            class_name=detection.class_name,
            track_id=track_id,
            detections=[detection],
        )
