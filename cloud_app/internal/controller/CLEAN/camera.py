import cv2
import numpy as np
from loguru import logger
from shapely.geometry import Point, Polygon

from cloud_app.internal.controller.base.camera import BaseCamera
from cloud_app.internal.controller.CLEAN.detection import Detection
from cloud_app.internal.controller.CLEAN.track import Track
from cloud_app.internal.pkg.box import is_two_boxs_intersecting, get_box_center, get_box_center_bottom, get_intersect_box, get_box_area, extend_bbox
from cloud_app.internal.pkg.geometry import is_point_inside_polygon
from cloud_app.internal.pkg.point import compute_distance
from cloud_app.common.config import AppConfigs

cfg = AppConfigs()
cfg.deploy_env = "NOTPRODUCTION"

class Camera(BaseCamera):
    tracked_objects: list[Track]
    ignore_track_ids: list[int]

    def __init__(self, cam_id: str, config: dict) -> None:
        super().__init__(cam_id, config)
        self.mhe_track: list[Track] = []
        self.product_track: list[Track] = []

    def update_tracks(
        self,
        detections: list[Detection],
        frame_id: int,
        video_url: str = None,
        DetectionType=Detection,
        TrackType=Track,
        frame=None,  ## only used for testing
        testing=False,
    ):
        display_frame = super().update_tracks(
            detections=detections,
            frame_id=frame_id,
            video_url=video_url,
            TrackType=TrackType,
            DetectionType=DetectionType,
            frame=frame,
            testing=testing,
        )
        
        return display_frame
    
    def base_check_track(self, track: Track) -> bool:
        """Check if the track is valid and not ignored."""

        return True
    
    def confidence_calculating(self, track: Track) -> float:
        """Calculate the event's confidence score"""
        confidence = 0.5
        return confidence

    def event_checking(self, frame_id: int, frame=None) -> tuple:
        event_detections = []
        event_confs = []
        for track in self.tracked_objects:
            if not self.base_check_track(track):
                continue

            if cfg.deploy_env not in ["PRODUCTION"]:
                """logging something"""

            
            # confidence = self.confidence_calculating(track)
            # event_detections.append(track.detections[-1])

            # ##TODO: update event confidence
            # event_confs.append(confidence)

            # self.ignore_track_ids.append(track.track_id)

        return event_detections, event_confs, frame