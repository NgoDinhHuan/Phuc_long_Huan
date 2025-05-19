from cloud_app.internal.controller.base.camera import BaseCamera
from cloud_app.internal.controller.hm08.track import Track
from cloud_app.internal.controller.hm08.detection import Detection
from cloud_app.internal.pkg.box import iou

class Camera(BaseCamera):
    def __init__(self, cam_id: str, config: dict) -> None:
        super().__init__(cam_id, config)
        self.next_track_id = 1
        self.tracked_objects = []

    def update_tracks(
        self, 
        detections: list[Detection], 
        frame_id: int, 
        frame=None, 
        testing: bool = False) -> None:
        iou_threshold = 0.4
        updated_tracks = []

        for det in detections:
            matched = False
            for track in self.tracked_objects:
                if not track.detections:
                    continue
                last_det = track.detections[-1]
                if iou(det.bbox, last_det.bbox) > iou_threshold:
                    det.track_id = track.track_id
                    track.detections.append(det)
                    updated_tracks.append(track)
                    matched = True
                    break
            if not matched:
                det.track_id = self.next_track_id
                new_track = Track.create(det, self.next_track_id, frame_id)
                self.next_track_id += 1
                updated_tracks.append(new_track)

        self.tracked_objects = updated_tracks

    def event_checking(self, frame_id: int, frame=None) -> tuple:
        event_detections = []
        event_confs = []
        for track in self.tracked_objects:
            idle_frames = track.calculate_idle_time()
            if idle_frames >= self.frame_threshold:
                event_detections.append(track.detections)
                event_confs.append(1.0)
        return event_detections, event_confs
