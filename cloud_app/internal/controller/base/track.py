from abc import ABC
from random import randint
from typing import Union

import cv2
import numpy as np
import supervision as sv
from shapely.geometry import LineString

from cloud_app.internal.pkg.point import get_center_point
from .detection import BaseDetection


def extend_bbox(bbox, min_margin=10, max_margin=100, margin_ratio=0.15):
    x_min, y_min, x_max, y_max = bbox
    w = x_max - x_min
    h = y_max - y_min
    x_margin = max(min_margin, w * margin_ratio, h * margin_ratio)
    x_margin = min(x_margin, max_margin)

    y_margin = max(min_margin, h * margin_ratio, w * margin_ratio)
    y_margin = min(y_margin, max_margin)
    return [
        x_min - x_margin,
        y_min - y_margin,
        x_max + x_margin,
        y_max + y_margin
    ]


class BaseTrack(ABC):
    def __init__(
        self,
        track_id: int,
        class_id: int,
        class_name: str,
        detections: list[BaseDetection] = [],
        violent_count: int = 0,
    ):
        self.detections = detections
        self.track_id = track_id
        self.class_id = class_id
        self.class_name = class_name
        self.missed_frames = []
        self.color = (randint(0, 255), randint(0, 255), randint(0, 255))
        self.already_warning = False
        self.violent_count = violent_count
        self.bbox = detections[-1].bbox if detections else None
        self.extended_bbox = None
        self.prev_bbox = None
        self.prev_bbox_keeper_count = 5

    def is_within_extended_bbox(self, bbox):
        # to skip the first frame
        if self.extended_bbox is None or bbox is None or self.prev_bbox is None:
            return False

        x_min, y_min, x_max, y_max = bbox
        ex_min, ey_min, ex_max, ey_max = self.extended_bbox
        return (ex_min <= x_min <= ex_max and
                ey_min <= y_min <= ey_max and
                ex_min <= x_max <= ex_max and
                ey_min <= y_max <= ey_max)

    def reset_miss(self):
        self.missed_frames = []

    def update_detection_stable(self, detection):
        new_bbox = detection.bbox
        if self.is_within_extended_bbox(new_bbox):
            # Update to new bbox
            detection.bbox = self.prev_bbox
            self.detections.append(detection)
            if self.prev_bbox_keeper_count > 0:
                self.bbox = self.prev_bbox
            else:
                # update prev_bbox
                self.bbox = new_bbox
                self.prev_bbox = new_bbox
            self.prev_bbox_keeper_count -= 1

        else:
            # Update to new extended bbox
            self.bbox = new_bbox
            self.prev_bbox = new_bbox
            self.extended_bbox = extend_bbox(new_bbox)
            self.detections.append(detection)
            self.prev_bbox_keeper_count = 5

    def update_detection(self, detection: BaseDetection):
        # self.detections.append(detection)
        # self.bbox = detection.bbox
        self.update_detection_stable(detection)
        self.reset_miss()

    def add_missed_frame(self, frame_id: int):
        self.missed_frames.append(frame_id)

    def get_simple_moving_line_string(self):
        if len(self.detections) < 2:
            return None
        start_point = get_center_point(self.detections[0].bbox)
        end_point = get_center_point(self.detections[-1].bbox)
        return LineString([start_point, end_point])

    def get_moving_line_string(self) -> Union[LineString, None]:
        if len(self.detections) < 2:
            return None
        box_center_points = []
        for detection in self.detections:
            box_center_points.append(get_center_point(detection.bbox))
        return LineString(box_center_points)

    def draw_moving_line(self, frame):
        if len(self.detections) < 2:
            return frame
        moving_line = [get_center_point(det.bbox) for det in self.detections]
        if moving_line:
            frame = cv2.polylines(
                frame,
                [np.array(moving_line)],
                isClosed=False,
                color=self.color,
                thickness=2,
            )
        return frame

    @property
    def missed_count(self):
        return len(self.missed_frames)

    @staticmethod
    def create(
        detection: BaseDetection,
        track_id: int,
        frame_id: int,
    ):
        return BaseTrack(
            class_id=detection.class_id,
            class_name=detection.class_name,
            track_id=track_id,
            detections=[detection],
        )

    @classmethod
    def track_to_sv_objects(cls, track_list: list) -> sv.Detections:
        xyxy_list = np.array([track.detections[-1].bbox for track in track_list])
        confidence_list = np.array(
            [track.detections[-1].confidence for track in track_list]
        )
        class_id_list = np.array([track.class_id for track in track_list])
        return sv.Detections(
            xyxy=xyxy_list,
            confidence=confidence_list,
            class_id=class_id_list,
        )
