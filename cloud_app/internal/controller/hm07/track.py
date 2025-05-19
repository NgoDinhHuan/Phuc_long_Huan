from cloud_app.internal.controller.base.track import BaseTrack
from cloud_app.internal.controller.hm07.detection import Detection


class Track(BaseTrack):

    def __init__(
        self,
        track_id: int,
        class_id: int,
        class_name: str,
        violent_count: int = 0,
        detections: list[Detection] = None,
    ):
        super().__init__(
            track_id=track_id,
            class_id=class_id,
            class_name=class_name,
            detections=detections,
            violent_count=violent_count,
        )

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
