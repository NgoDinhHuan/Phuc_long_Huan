from datetime import datetime
from cloud_app.internal.controller.base.detection import BaseDetection


class Detection(BaseDetection):
    def __init__(
        self,
        msg: dict,
        frame_id: int,
        cam_id: str,
        video_url: str,
        image_size=(1920, 1080),
        extra_information: dict = {}
    ):
        super().__init__(
            msg=msg,
            frame_id=frame_id,
            cam_id=cam_id,
            video_url=video_url,
            image_size=image_size,
            extra_information=extra_information
        )
