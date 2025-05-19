import math


def get_center_point(box: list) -> (int, int):
    x1, y1, x2, y2 = box
    return int((x1 + x2) // 2), int((y1 + y2) // 2)


def compute_distance(p1: list, p2: list) -> float:
    x1, y1 = p1
    x2, y2 = p2
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
