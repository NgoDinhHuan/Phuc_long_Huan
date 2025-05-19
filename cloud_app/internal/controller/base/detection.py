from abc import ABC

import numpy as np
import supervision as sv
from loguru import logger


def padding_bbox_arr(bbox_arr: np.ndarray, padx=10, pady=10, pad_ratio=0.0):
    # padding 5% of bbox size
    if pad_ratio > 0:
        w = bbox_arr[:, 2] - bbox_arr[:, 0]
        h = bbox_arr[:, 3] - bbox_arr[:, 1]
        padx = (w * pad_ratio).astype(int)
        pady = (h * pad_ratio).astype(int)

    return np.array([
        np.maximum(0, bbox_arr[:, 0] - padx),
        np.maximum(0, bbox_arr[:, 1] - pady),
        np.minimum(1920, bbox_arr[:, 2] + padx),
        np.minimum(1080, bbox_arr[:, 3] + pady),
    ]).T


class BaseDetection(ABC):
    def __init__(
        self,
        msg: dict,
        frame_id: int,
        cam_id: any,
        video_url: str,
        image_size=(1920, 1080),
        extra_information: dict = {}
    ):
        self.frame_id = frame_id
        self.cam_id = cam_id
        self.video_url = video_url
        self.confidence = msg["confidence"]
        self.class_id = msg["class_id"]
        self.class_name = msg["class_name"]
        self.detect_time = msg["detect_time"]
        self.bbox = self.process_bbox(msg["xyxy"], image_size=image_size)
        self.track_id = msg.get("track_id", -1)
        self.extra_information = extra_information

    def to_dict(self):
        return {
            "confidence": self.confidence,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "track_id": self.track_id,
            "bbox": self.bbox,
            "detect_time": self.detect_time,
            "frame_id": self.frame_id,
            "cam_id": self.cam_id,
            "video_url": self.video_url,
            "extra_information": self.extra_information
        }

    def process_bbox(self, bbox, image_size=(1920, 1080), padx=1, pady=1, pad_ratio=0.0):
        x1, y1, x2, y2 = bbox
        x1 = x1 * image_size[0] / 1920
        x2 = x2 * image_size[0] / 1920
        y1 = y1 * image_size[1] / 1080
        y2 = y2 * image_size[1] / 1080
        bbox = [int(x1), int(y1), int(x2), int(y2)]

        # padding 5% of bbox size
        if pad_ratio > 0:
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            padx = int(w * pad_ratio)
            pady = int(h * pad_ratio)

        bbox[0] = max(0, bbox[0] - padx)
        bbox[1] = max(0, bbox[1] - pady)
        bbox[2] = min(image_size[0], bbox[2] + padx)
        bbox[3] = min(image_size[1], bbox[3] + pady)

        return bbox

    @classmethod
    def detections_to_sv_detections(
        cls,
        ds_detections: list,
    ) -> sv.Detections:
        """
        Convert current app detections to sv.Detections
        """
        xyxy_list = np.array([det.bbox for det in ds_detections])
        class_ids = np.array([det.class_id for det in ds_detections])
        confidence_scores = np.array([det.confidence for det in ds_detections])

        class_names = [det.class_name for det in ds_detections]
        frame_ids = [det.frame_id for det in ds_detections]
        cam_ids = [det.cam_id for det in ds_detections]
        detect_times = [det.detect_time for det in ds_detections]
        video_urls = [det.video_url for det in ds_detections]
        extra_informations = [det.extra_information for det in ds_detections]

        data = {
            "class_name": class_names,
            "frame_id": frame_ids,
            "cam_id": cam_ids,
            "detect_time": detect_times,
            "video_url": video_urls,
            "org_bbox": xyxy_list,
            "extra_informations": extra_informations
        }
        # add padding to bbox before sending to supervision
        xyxy_list = padding_bbox_arr(xyxy_list, padx=10, pady=10)
        sv_detections = sv.Detections(
            xyxy=xyxy_list,
            confidence=confidence_scores,
            class_id=class_ids,
            data=data,
        )
        return sv_detections

    @classmethod
    def sv_detections_to_detections(
        cls,
        sv_detections: sv.Detections,
    ) -> list:
        """
        Convert sv.Detections to current app detections
        """
        if len(sv_detections) == 0:
            # logger.info("No detections in sv_detections")
            return []

        detections = []
        # xyxy_list = sv_detections.xyxy.tolist()
        xyxy_list = sv_detections.data["org_bbox"].tolist()
        confidence_scores = sv_detections.confidence.tolist()
        class_ids = sv_detections.class_id.tolist()
        track_ids = sv_detections.tracker_id.tolist()
        class_names = sv_detections.data["class_name"]
        frame_ids = sv_detections.data["frame_id"]
        cam_ids = sv_detections.data["cam_id"]
        detect_times = sv_detections.data["detect_time"]
        video_urls = sv_detections.data["video_url"]
        extra_informations = sv_detections.data["extra_informations"]

        for i in range(len(xyxy_list)):
            try:
                detections.append(
                    cls(
                        msg={
                            "xyxy": xyxy_list[i],
                            "confidence": confidence_scores[i],
                            "class_id": class_ids[i],
                            "class_name": class_names[i],
                            "track_id": track_ids[i],
                            "detect_time": detect_times[i],
                        },
                        frame_id=frame_ids[i],
                        cam_id=cam_ids[i],
                        video_url=video_urls[i],
                        extra_information=extra_informations[i]
                    )
                )
            except Exception as e:
                logger.error(f"Parse sv detection error: {e}")
        return detections
