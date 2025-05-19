from shapely.geometry import Point
from shapely.geometry import Point, MultiPoint
from shapely.geometry import Polygon, LineString
import numpy as np

def is_point_inside_polygon(point: Point, polygon: Polygon) -> bool:
    if not isinstance(point, Point):
        point = Point(point)
    if not isinstance(polygon, Polygon):
        polygon = Polygon(polygon)
    return polygon.contains(point)


def is_line_crossing_polygon(line: LineString, polygon: Polygon) -> bool:
    return line.crosses(polygon)


def is_two_lines_intersect(line1: list, line2: list) -> bool:
    x1, y1 = line1[0]
    x2, y2 = line1[1]
    x3, y3 = line2[0]
    x4, y4 = line2[1]
    a1 = y2 - y1
    b1 = x1 - x2
    c1 = a1 * x1 + b1 * y1
    a2 = y4 - y3
    b2 = x3 - x4
    c2 = a2 * x3 + b2 * y3
    determinant = a1 * b2 - a2 * b1
    if determinant == 0:
        return False
    x = (b2 * c1 - b1 * c2) / determinant
    y = (a1 * c2 - a2 * c1) / determinant
    if (
        min(x1, x2) <= x <= max(x1, x2)
        and min(x3, x4) <= x <= max(x3, x4)
        and min(y1, y2) <= y <= max(y1, y2)
        and min(y3, y4) <= y <= max(y3, y4)
    ):
        return True
    return False


def get_intersection_point(
    line1: LineString | list, line2: LineString | list
) -> list[Point]:
    if isinstance(line1, list):
        line1 = LineString(line1)
    if isinstance(line2, list):
        line2 = LineString(line2)
    intersection = line1.intersection(line2)
    if isinstance(intersection, Point):
        return [intersection]
    elif isinstance(intersection, MultiPoint):
        return list(intersection.geoms)
    return []

def direction_two_lines(
    line1: LineString | list, line2: LineString | list
) -> float:

    coords1 = np.array(line1.coords)
    coords2 = np.array(line2.coords)

    vector1 = coords1[-1] - coords1[0]
    vector2 = coords2[-1] - coords2[0]
    
    cos_theta = np.dot(vector1, vector2) / (np.linalg.norm(vector1) * np.linalg.norm(vector2))
    theta = np.arccos(np.clip(cos_theta, -1.0, 1.0)) 
    theta_degrees = np.degrees(theta)

    return theta_degrees