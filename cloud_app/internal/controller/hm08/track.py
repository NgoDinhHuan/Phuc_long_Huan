# track.py

from cloud_app.internal.controller.base.track import BaseTrack
from cloud_app.internal.controller.hm08.detection import Detection
from scipy.spatial.distance import cdist
from scipy.optimize import linear_sum_assignment
import numpy as np

#TRACK 
class Track(BaseTrack):
    def __init__(
        self,
        track_id, 
        class_id, 
        class_name, 
        detections=None, 
        start_frame=None, 
        frame_id=0, 
        bbox=None):
        super().__init__(track_id, class_id, class_name, detections or [])
        self.start_frame = start_frame if start_frame is not None else (detections[0].frame_id if detections else frame_id)
        self.last_frame = frame_id
        self.hits = 1
        self.miss = 0
        if bbox:
            self.bbox = bbox  

    def calculate_idle_time(self):
        if not self.detections:
            return 0
        return self.detections[-1].frame_id - self.start_frame

    @staticmethod
    def create(detection: Detection, track_id: int, frame_id: int):
        return Track(track_id=track_id,
                     class_id=detection.class_id,
                     class_name=detection.class_name,
                     detections=[detection],
                     start_frame=frame_id,
                     frame_id=frame_id,
                     bbox=detection.bbox)

# SIMPLE TRACKER 
class SimpleTracker:
    def __init__(self, max_miss=30, distance_threshold=80, iou_threshold=0.3):
        self.next_id = 1
        self.tracks = []
        self.max_miss = max_miss
        self.distance_threshold = distance_threshold
        self.iou_threshold = iou_threshold

    def update(self, detections: list[np.ndarray], frame_id: int) -> list:
        matched, unmatched_dets, unmatched_tracks = self._match(detections)
        results = []

        for det_idx, trk_idx in matched:
            det = detections[det_idx]
            track = self.tracks[trk_idx]
            track.bbox = det
            track.last_frame = frame_id
            track.hits += 1
            track.miss = 0
            results.append((track.track_id, track.bbox))

        for idx in unmatched_dets:
            bbox = detections[idx]
            new_track = Track(
                track_id=self.next_id, 
                class_id=0, 
                class_name='person', 
                bbox=bbox, 
                frame_id=frame_id)
            self.tracks.append(new_track)
            results.append((new_track.track_id, new_track.bbox))
            self.next_id += 1

        for idx in unmatched_tracks:
            self.tracks[idx].miss += 1

        self.tracks = [t for t in self.tracks if t.miss <= self.max_miss]
        return results

    def _match(self, detections):
        if len(self.tracks) == 0:
            return [], list(range(len(detections))), []
        if len(detections) == 0:
            return [], [], list(range(len(self.tracks)))

        track_boxes = [t.bbox for t in self.tracks]
        track_centers = np.array([self._get_center(b) for b in track_boxes])
        det_centers = np.array([self._get_center(b) for b in detections])

        dists = cdist(track_centers, det_centers)
        ious = self._compute_iou(track_boxes, detections)
        cost_matrix = (1 - ious) + dists / 1000.0

        trk_indices, det_indices = linear_sum_assignment(cost_matrix)

        matched = []
        unmatched_dets = set(range(len(detections)))
        unmatched_tracks = set(range(len(self.tracks)))

        for trk_idx, det_idx in zip(trk_indices, det_indices):
            if ious[trk_idx][det_idx] >= self.iou_threshold or dists[trk_idx][det_idx] <= self.distance_threshold:
                matched.append((det_idx, trk_idx))
                unmatched_dets.discard(det_idx)
                unmatched_tracks.discard(trk_idx)

        return matched, list(unmatched_dets), list(unmatched_tracks)

    def _get_center(self, box):
        x1, y1, x2, y2 = box
        return [(x1 + x2) / 2, (y1 + y2) / 2]

    def _compute_iou(self, boxes1, boxes2):
        ious = np.zeros((len(boxes1), len(boxes2)))
        for i, box1 in enumerate(boxes1):
            for j, box2 in enumerate(boxes2):
                ious[i, j] = self._iou(box1, box2)
        return ious

    def _iou(self, box1, box2):
        xA = max(box1[0], box2[0])
        yA = max(box1[1], box2[1])
        xB = min(box1[2], box2[2])
        yB = min(box1[3], box2[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = max(1, (box1[2] - box1[0]) * (box1[3] - box1[1]))
        boxBArea = max(1, (box2[2] - box2[0]) * (box2[3] - box2[1]))
        return interArea / (boxAArea + boxBArea - interArea + 1e-5)
