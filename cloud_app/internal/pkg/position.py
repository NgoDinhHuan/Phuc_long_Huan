from .box import iou
from .point import compute_distance, get_center_point


def is_moving(
    box1: list, box2: list, iou_threshold: float = 0.8, distance_threshold: float = 0.05
) -> bool:
    iou_score = iou(box1, box2)
    if iou_score > iou_threshold:
        return False
    p1 = get_center_point(box1)
    p2 = get_center_point(box2)
    center_distance = compute_distance(p1, p2)
    box_width = box1[2] - box1[0]
    if center_distance / box_width < distance_threshold:
        return False
    return True


def is_not_moving(
    box1: list, box2: list, iou_threshold: float = 0.8, distance_threshold: float = 0.05
) -> bool:
    return not is_moving(box1, box2, iou_threshold, distance_threshold)

def is_moving_xcenter(
    box1: list, box2: list, iou_threshold: float = 0.8, distance_threshold: float = 0.05
) -> bool:
    iou_score = iou(box1, box2)
    if iou_score > iou_threshold:
        return False
    p1x, _ = get_center_point(box1)
    p2x, _ = get_center_point(box2)
    xcenter_distance = abs(p1x - p2x)
    box_width = box1[2] - box1[0]
    if xcenter_distance / box_width < distance_threshold:
        return False
    return True
