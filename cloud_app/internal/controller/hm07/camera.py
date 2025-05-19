from loguru import logger

from cloud_app.internal.controller.base.camera import BaseCamera
from cloud_app.internal.controller.hm07.detection import Detection
from cloud_app.internal.controller.hm07.track import Track
from cloud_app.internal.pkg.position import is_moving
from cloud_app.common.logs_track import logs_infor
from cloud_app.common.config import cfg

class Camera(BaseCamera):
    tracked_objects: list[Track]
    ignore_track_ids: list[int]

    def __init__(self, cam_id: str, config: dict) -> None:
        super().__init__(cam_id, config)

    def update_tracks(
        self,
        detections: list[Detection],
        frame_id: int,
        TrackType=Track,
        DetectionType=Detection,
        video_url: str = None,
        frame=None,  ## only used for testing
        testing=False,
    ):
        return super().update_tracks(
            detections=detections,
            frame_id=frame_id,
            video_url=video_url,
            TrackType=TrackType,
            DetectionType=DetectionType,
            frame=frame,
            testing=testing,
        )

    def event_checking(self, frame_id: int, frame=None) -> tuple:
        event_detections = []
        event_confs = []
        if cfg.deploy_env not in ["PRODUCTION"]:
            logs_infor(self, frame_id)
        for track in self.tracked_objects:
            if (
                track.track_id in self.ignore_track_ids
                or track.detections[-1].confidence < 0.5
            ):
                continue

            if track.detections[-1].class_name not in self.config["target_class"] or track.class_name not in self.config["target_class"]:
                continue

            if len(track.detections) < 2:
                continue

            # Get the index from where the object was last considered inactive
            inactive_box_idx = max(0, track.violent_count)

            # Check if the object has been moving
            if not is_moving(track.detections[-1].bbox, track.detections[inactive_box_idx].bbox, distance_threshold=0.15):
                timestrame_begin = int(track.detections[inactive_box_idx].extra_information["startTime"]) + int(track.detections[inactive_box_idx].frame_id // 25)
                timestrame_end = int(track.detections[-1].extra_information["startTime"]) + int(track.detections[-1].frame_id // 25)
                track_time = (timestrame_end - timestrame_begin)
            else:
                # Reset the track time if the object moves
                # Save the index of the last moving detection
                track_time = 0
                track.violent_count = len(track.detections) - 1  

            # If the track has been inactive for longer than the configured limit
            if track_time > self.config["limit_time"]:
                # Filter out detections with confidence greater than 0.5
                confidence_values = [det.confidence for det in track.detections[track.violent_count:] if det.confidence > 0.5]
                confidence_values.sort()

                #cal confidence of event
                mean_conf = sum(confidence_values) / len(confidence_values)
                median_conf = confidence_values[(len(confidence_values)//2)]
                len_conf = len(confidence_values) / (self.config["limit_time"] * 4)

                logger.info(f"Track_id {track.track_id}, Mean confidence: {mean_conf}, Median confidence: {median_conf}, Number of bbox: {len(confidence_values)}")
                if median_conf >= self.config["median_conf_threshold"] and mean_conf >= self.config["mean_conf_threshold"] and len(confidence_values) >= track_time//2:
                    logger.info("Event Accepted")
                    event_detections.append(track.detections[track.violent_count:])
                    
                    # Calculate the confidence of the event 
                    event_conf = 0.4 * mean_conf + 0.2 * median_conf + 0.4 * len_conf                
                    event_confs.append(event_conf)

                    self.ignore_track_ids.append(track.track_id)  
                else:
                    track.violent_count = len(track.detections) - 1
                    logger.info("Event Rejected")

        return event_detections, event_confs, frame