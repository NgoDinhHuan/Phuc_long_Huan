from cloud_app.internal.controller.base.detection import BaseDetection
import time

class Detection(BaseDetection):
    def __init__(
        self, 
        track_id: int, 
        class_id: int, 
        class_name: str, 
        bbox: tuple, 
        frame_id: int, 
        video_url: str):
        msg = {
            "confidence": 1.0,
            "class_id": class_id,
            "class_name": class_name,
            "xyxy": bbox,
            "frame_id": int(frame_id),  
            "detect_time": time.time()
        }
        super().__init__(msg, bbox, int(frame_id), video_url)  #
        self.track_id = track_id
        self.frame_id = int(frame_id)  

    @classmethod
    def from_yolo(cls, results, frame_id, cam_id, video_url):
        """
        Convert YOLO results thành danh sách Detection.
        """
        detections = []
        class_ids = results.boxes.cls.cpu().numpy()
        boxes = results.boxes.xyxy.cpu().numpy()

        for box, class_id in zip(boxes, class_ids):
            x1, y1, x2, y2 = box
            bbox = (x1, y1, x2, y2)
            class_name = results.names[int(class_id)]
            det = cls(
                track_id=None,
                class_id=int(class_id),
                class_name=class_name,
                bbox=bbox,
                frame_id=int(frame_id),  
                video_url=video_url
            )
            detections.append(det)

        return detections
