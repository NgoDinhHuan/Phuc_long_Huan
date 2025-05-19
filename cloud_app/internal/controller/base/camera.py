import time
from abc import ABC, abstractmethod

import sys
import cv2
import numpy as np
import supervision as sv
from loguru import logger
from shapely.geometry import Point, Polygon

from cloud_app.common.uts_warehouse import (
    is_person,
    is_forklift_vehicle,
    is_security_person,
)
from cloud_app.internal.controller.base.detection import BaseDetection
from cloud_app.internal.controller.base.event import BaseEvent
from cloud_app.internal.controller.base.track import BaseTrack
from cloud_app.internal.pkg.box import is_two_boxs_intersecting
from cloud_app.internal.pkg.geometry import is_point_inside_polygon
from cloud_app.internal.pkg.point import get_center_point


class BaseCamera(ABC):
    tracked_objects: list[BaseTrack]
    ignore_track_ids: list[int]
    camera_fps = 4
    max_miss_track = 20 # 20 / 4 = 5 seconds
    minimum_consecutive_frames = 3

    def __init__(self, cam_id: str, config: dict) -> None:
        self.cam_id = cam_id
        self.config = config
        self.max_miss_track = self.config.get("max_miss", self.max_miss_track)
        self.tracked_objects = []
        self.ignore_track_ids = []
        self.current_detections = []
        self.warned_track_ids = []

        self.tracker = sv.ByteTrack(frame_rate=self.camera_fps,
                                    lost_track_buffer=self.max_miss_track,
                                    minimum_consecutive_frames=self.minimum_consecutive_frames)

        self.remain_track_dict = {}

        self.check_time_for_logging = time.time()


    def update_tracks(
        self,
        detections: list[BaseDetection],
        frame_id: int,
        video_url: str = None,
        TrackType=BaseTrack,
        DetectionType=BaseDetection,
        frame=None,  ## only used for testing
        testing=False,
    ):
        # logger.info(
        #     f"Process cam_id {self.cam_id} frame id {frame_id}. Number of detections {len(detections)}"
        # )
        display_frame = None
        self.warned_track_ids = self.warned_track_ids[-50:]
        CAM_W, CAM_H = self.config["cam_resolution"]
        self.current_detections = []

        if detections:
            ## tracking with supervision's Tracker
            sv_detections = DetectionType.detections_to_sv_detections(
                detections
            )
            sv_detections = self.tracker.update_with_detections(sv_detections)
            assert len(sv_detections) == len(sv_detections.tracker_id)

            self.current_detections = DetectionType.sv_detections_to_detections(
                sv_detections
            )

            #### only use for testing,
            #### dont forget to change save_dir if u deploy in other server
            if testing:
                display_frame = np.zeros((CAM_H, CAM_W, 3), dtype=np.uint8)
                if frame is not None:
                    display_frame = frame.copy()
                labels = [
                    f"#{tracker_id}" for tracker_id in sv_detections.tracker_id
                ]
                ## draw bbox and label to frame
                label_annotator = sv.LabelAnnotator()
                box_annotator = sv.BoundingBoxAnnotator()
                display_frame = label_annotator.annotate(
                    scene=display_frame, detections=sv_detections, labels=labels
                )
                display_frame = box_annotator.annotate(
                    display_frame, detections=sv_detections
                )
                ## puttext frame_id to display_frame
                cv2.putText(
                    display_frame,
                    f"Frame {frame_id}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )
                ## draw camera area
                if "cam_zones" in self.config:
                    for cam_zone in self.config["cam_zones"]:
                        display_frame = cv2.polylines(
                            display_frame,
                            [np.array(cam_zone)],
                            isClosed=True,
                            color=(0, 255, 0),
                            thickness=2,
                        )
        else:
            self.tracker.update_with_detections(sv.Detections.empty())

        current_track_dict = {det.track_id: det for det in self.current_detections if det.track_id not in self.ignore_track_ids}

        for track_id in list(self.remain_track_dict.keys()):
            # remove track if it's in ignore_track_ids first to release memory
            if track_id in self.ignore_track_ids:
                del self.remain_track_dict[track_id]
                continue

            if track_id not in current_track_dict:
                # add missed frame
                self.remain_track_dict[track_id].add_missed_frame(frame_id)

                # remove track if it has missed too many frames
                if self.remain_track_dict[track_id].missed_count > self.max_miss_track:
                    del self.remain_track_dict[track_id]
                    logger.info(f"Remove track {track_id} from camera {self.cam_id}")

                    # remove track_id from ignore_track_ids. bc it's not tracked anymore, byte_track will create new track_id for it
                    if track_id in self.ignore_track_ids:
                        self.ignore_track_ids.remove(track_id)


        for new_track_id in current_track_dict:
            if new_track_id in self.remain_track_dict:
                # update track
                self.remain_track_dict[new_track_id].update_detection(current_track_dict[new_track_id])
            else:
                # create new track
                self.remain_track_dict[new_track_id] = TrackType.create(
                    detection=current_track_dict[new_track_id],
                    track_id=new_track_id,
                    frame_id=frame_id,
                )
                logger.info(f"Create new track {new_track_id} in camera {self.cam_id}")

        self.tracked_objects = list(self.remain_track_dict.values())

        if display_frame is not None:
            for track in self.tracked_objects:
                display_frame = track.draw_moving_line(frame=display_frame)

        ## remove outside object track
        self.tracked_objects = [
            track
            for track in self.tracked_objects
            if self.check_in_camera_area(track)
            and (track.track_id not in self.ignore_track_ids)
        ]

        # log memory usage if it's too high (> 50MB). log every 30 seconds
        if sys.getsizeof(self.remain_track_dict) > 50 * 1024 * 1024 and self.check_time_for_logging - time.time() > 30 == 0:
            logger.info("====================================")
            logger.info(f"Memory usage of remain_track_dict in camera {self.cam_id}: {sys.getsizeof(self.remain_track_dict)} bytes")
            logger.info(f"Number of tracks in camera {self.cam_id}: {len(self.remain_track_dict)}")
            logger.info(f"Number of ignore tracks in camera {self.cam_id}: {len(self.ignore_track_ids)}")
            logger.info("====================================")

            self.check_time_for_logging = time.time()


        return display_frame

    def check_in_camera_area(self, obj_bbox: BaseTrack | BaseDetection):
        """
        Check if object is in camera area
        """
        if "cam_zones" not in self.config or len(self.config["cam_zones"]) < 1:
            return True
        for cam_zone in self.config["cam_zones"]:
            if is_point_inside_polygon(
                point=Point(get_center_point(obj_bbox.bbox)),
                polygon=Polygon(cam_zone),
            ):
                return True
        return False

    @abstractmethod
    def event_checking(self, *args) -> tuple:
        pass

    def create_event(
        self,
        event_name: str,
        detections: list[BaseDetection],
        event_conf: float,
        frame_id: int,
        push_time: float | None = None,
    ) -> dict:
        return BaseEvent(
            name=event_name,
            detections=detections,
            event_conf=event_conf,
            camera_id=self.cam_id,
            frame_id=frame_id,
            push_time=push_time,
            tenant_id=self.config.get("tenant_id", ""),
            area_name=self.config.get("area_name", ""),
        ).to_dict()

    def check_person_operator_forklift(self, person_track: BaseTrack) -> bool:
        if not is_person(person_track.class_name):
            return False
        for obj_track in self.tracked_objects:
            class_name = obj_track.class_name.lower().replace(" ", "_")
            if not is_forklift_vehicle(class_name):
                continue
            if is_two_boxs_intersecting(person_track.bbox, obj_track.bbox):
                return True
        return False
