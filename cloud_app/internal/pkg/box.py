import cv2


def iou(box1: list, box2: list) -> float:
    """
    Calculate intersection over union
    :param box1: a[0], a[1], a[2], a[3] <-> left, top, right, bottom
    :param box2: b[0], b[1], b[2], b[3] <-> left, top, right, bottom
    """
    w_intersect = max(0, (min(box1[2], box2[2]) - max(box1[0], box2[0])))
    h_intersect = max(0, (min(box1[3], box2[3]) - max(box1[1], box2[1])))
    s_intersect = w_intersect * h_intersect
    s_a = (box1[2] - box1[0]) * (box1[3] - box1[1])
    s_b = (box2[2] - box2[0]) * (box2[3] - box2[1])
    return float(s_intersect) / (s_a + s_b - s_intersect)


def draw_box_simple(img, box, color=(0, 255, 0), label=""):
    x1, y1, x2, y2 = list(map(int, box))
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    cv2.putText(
        img,
        label,
        (x1, y1 - 10),
        1,
        1,
        color,
        thickness=2,
        lineType=cv2.LINE_AA,
    )
    return img

def draw_bb(img, box, color, label=""):
    x1, y1, x2, y2 = list(map(int, box))
    len_h = min(150, int(0.2 * (y2 - y1)))
    len_w = min(150, int(0.2 * (x2 - x1)))
    line_tn = 2

    cv2.line(img, (x1, y1), (x1 + len_w, y1), color, line_tn)
    cv2.line(img, (x1, y1), (x1, y1 + len_h), color, line_tn)
    cv2.line(img, (x2, y2), (x2 - len_w, y2), color, line_tn)
    cv2.line(img, (x2, y2), (x2, y2 - len_h), color, line_tn)
    cv2.line(img, (x1, y2), (x1 + len_w, y2), color, line_tn)
    cv2.line(img, (x1, y2), (x1, y2 - len_h), color, line_tn)

    cv2.line(img, (x2, y1), (x2 - len_w, y1), color, line_tn)
    cv2.line(img, (x2, y1), (x2, y1 + len_h), color, line_tn)

    font_scale = 1
    font_thickness = 2
    text_size, baseline = cv2.getTextSize(label, fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                                          fontScale=font_scale, thickness=font_thickness)
    if y1 - len_h > 20:
        top_center = (int((x1 + x2) / 2), y1)
        text_point = (top_center[0] + len_h, top_center[1] - len_h)
        cv2.circle(img, top_center, radius=2, color=color, thickness=-1)
        cv2.line(img, top_center, text_point, color=color, thickness=1)
        cv2.line(
            img,
            text_point,
            (text_point[0] + text_size[0], text_point[1]),
            color=color,
            thickness=1,
        )
        cv2.putText(
            img,
            label,
            (text_point[0], text_point[1] - 5),
            1,
            2,
            color,
            thickness=2,
            lineType=cv2.LINE_AA,
        )
    else:
        bottom_center = (int((x1 + x2) / 2), y2)
        text_point = (bottom_center[0] + len_h, bottom_center[1] + len_h + 10)
        cv2.line(img, bottom_center, text_point, color=color, thickness=1)
        cv2.circle(img, bottom_center, radius=3, color=color, thickness=-1)
        cv2.putText(img,
                    label,
                    (text_point[0], text_point[1] - 5),
                    1,
                    2,
                    color,
                    thickness=2,
                    lineType=cv2.LINE_AA,
                    )
        cv2.line(
            img,
            text_point,
            (text_point[0] + text_size[0], text_point[1]),
            color=color,
            thickness=1,
        )
    overlay = img.copy()
    cv2.rectangle(
        img,
        (int(x1), int(y1)),
        (int(x2), int(y2)),
        color=(0, 0, 255),
        thickness=-1,
    )
    alpha = 0.8  # Transparency factor.
    # Following line overlays transparent rectangle
    # over the image
    img_new = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)
    return img_new
# vẽ bb cho rule hm08
def draw_bb_hm08(img, box, color=(0, 255, 0), label=""):
    """
    Hàm vẽ bbox đơn giản dành riêng cho rule HM08:
    - Vẽ viền
    - Ghi label rõ ràng
    - Không fill, không overlay
    """
    x1, y1, x2, y2 = map(int, box)
    cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness=2)

    if label:
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        label_bg = (x1, y1 - th - 4, x1 + tw + 4, y1)  

        cv2.putText(
            img,
            label,
            (x1 + 2, y1 - 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            thickness=2,
            lineType=cv2.LINE_AA
        )
    return img

def crop_image_with_bbox(img, box, box_format="xyxy"):
    """ """
    x1, y1, x2, y2 = box
    if box_format == "xywh":
        x, y, w, h = box
        x1, y1, x2, y2 = (x - w / 2), (y - h / 2), (x + w / 2), (y + h / 2)

    img_h, img_w, _ = img.shape
    if (x1 < 1) and (y1 < 1) and (x2 < 1) and (y2 < 1):
        x1 = x1 * img_w
        y1 = y1 * img_h
        x2 = x2 * img_w
        y2 = y2 * img_h
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    crop_img = img[y1:y2, x1:x2, :]
    return crop_img


def crop_image_with_padding(img, bbox: list[int], padding_ratio=0.3):
    x1, y1, x2, y2 = bbox
    h, w, _ = img.shape
    x_center = (x1 + x2) // 2
    y_center = (y1 + y2) // 2
    box_w = x2 - x1
    box_h = y2 - y1

    # add padding
    box_w = box_w + int(box_w * padding_ratio)
    box_h = box_h + int(box_h * padding_ratio)
    x1 = x_center - box_w // 2
    x2 = x_center + box_w // 2
    y1 = y_center - box_h // 2
    y2 = y_center + box_h // 2
    x1 = int(max(0, x1))
    y1 = int(max(0, y1))
    x2 = int(min(x2, w))
    y2 = int(min(y2, h))
    return img[y1:y2, x1:x2, :]


def is_two_boxs_intersecting(box1: list, box2: list) -> bool:
    return not (
            box1[2] < box2[0]
            or box1[0] > box2[2]
            or box1[3] < box2[1]
            or box1[1] > box2[3]
    )


def get_union_box(boxes: list[list[int]]) -> list[int]:
    x1 = min([box[0] for box in boxes])
    y1 = min([box[1] for box in boxes])
    x2 = max([box[2] for box in boxes])
    y2 = max([box[3] for box in boxes])
    return [x1, y1, x2, y2]


def get_intersect_box(box1: list, box2: list) -> list:
    """
    Args:
        box1: [x1, y1, x2, y2] -> left, top, right, bottom
        box2: [x1, y1, x2, y2] -> left, top, right, bottom
    """
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    return [x1, y1, x2, y2]


def get_box_area(box: list) -> float:
    return (box[2] - box[0]) * (box[3] - box[1])


def extend_bbox(bbox, box_format="xyxy", min_margin=10, max_margin=100, margin_ratio=0.1, max_size=(1920, 1080)):
    """
    Args:
        bbox: [x1, y1, x2, y2] -> left, top, right, bottom
        box_format: str -> "xyxy" or "xywh"
        min_margin: int -> minimum margin
        max_margin: int -> maximum margin
        margin_ratio: int | float | list -> (margin ratio x, margin ratio y)
        max_size: tuple -> maximum size
    Returns: [x1, y1, x2, y2] -> left, top, right, bottom
    """
    if box_format == "xywh":
        x, y, w, h = bbox
    else:
        x, y, w, h = convert_xyxy_to_xywh(bbox)

    if isinstance(margin_ratio, (int, float)):
        margin_ratio = [margin_ratio, margin_ratio]

    x_margin = max(min_margin, w * margin_ratio[0])
    y_margin = max(min_margin, h * margin_ratio[1])
    x_margin = min(x_margin, max_margin)
    y_margin = min(y_margin, max_margin)
    return [
        int(max(x - x_margin - w // 2, 0)),
        int(max(y - y_margin - h // 2, 0)),
        int(min(x + x_margin + w // 2, max_size[0])),
        int(min(y + y_margin + h // 2, max_size[1])),
    ]


def convert_xyxy_to_xywh(bbox: list) -> list:
    x1, y1, x2, y2 = bbox
    return [int((x1 + x2) / 2), int((y1 + y2) / 2), x2 - x1, y2 - y1]


def convert_xywh_to_xyxy(bbox: list) -> list:
    x, y, w, h = bbox
    return [x - w // 2, y - h // 2, x + w // 2, y + h // 2]


def is_within_extended_bbox(bbox, next_bbox, box_format="xyxy"):
    """
    Args:
        bbox: [x1, y1, x2, y2] -> left, top, right, bottom
        next_bbox: [x1, y1, x2, y2] -> left, top, right, bottom
        box_format: str -> "xyxy" or "xywh"
    Returns: bool
    """
    if box_format == "xywh":
        bbox = convert_xywh_to_xyxy(bbox)
        next_bbox = convert_xywh_to_xyxy(next_bbox)

    nx_min, ny_min, nx_max, ny_max = next_bbox
    x_min, y_min, x_max, y_max = bbox
    return (x_min <= nx_min <= x_max and
            y_min <= ny_min <= y_max and
            x_min <= nx_max <= x_max and
            y_min <= ny_max <= y_max)


def get_box_xcenter(box: list) -> int:
    return int((box[0] + box[2]) // 2)


def get_box_ycenter(box: list) -> int:
    return int((box[1] + box[3]) // 2)


def get_box_center(box: list):
    return (get_box_xcenter(box), get_box_ycenter(box))

def get_box_center_bottom(box: list):
    return (get_box_xcenter(box), box[3])

def bbox_similarity(bbox1, bbox2, threshold=0.8):
        """
        So sánh độ tương đồng về chiều dài và chiều rộng của 2 bbox.
        
        :param bbox1: Bounding box đầu tiên, dạng (x1, y1, x2, y2)
        :param bbox2: Bounding box thứ hai, dạng (x1, y1, x2, y2)
        :param threshold: Ngưỡng tương đồng (mặc định là 0.8 tức là 80%)
        :return: True nếu độ tương đồng trên ngưỡng, False nếu không
        """
        # Tính chiều rộng và chiều dài của bbox
        width1 = bbox1[2] - bbox1[0]
        height1 = bbox1[3] - bbox1[1]
        width2 = bbox2[2] - bbox2[0]
        height2 = bbox2[3] - bbox2[1]
        
        # Tính tỷ lệ tương đồng cho chiều rộng và chiều dài
        width_similarity = min(width1, width2) / max(width1, width2)
        height_similarity = min(height1, height2) / max(height1, height2)
        
        # Kiểm tra nếu cả hai tỷ lệ đều trên ngưỡng
        if width_similarity >= threshold and height_similarity >= threshold:
            return True
        else:
            return False
        
def draw_line(frame, line, color=(0, 0, 255), thickness=2):
    pt1 = (int(line[0][0]), int(line[0][1]))
    pt2 = (int(line[1][0]), int(line[1][1]))
    cv2.line(frame, pt1, pt2, color, thickness)
    return frame

def merge_two_xyxy_boxes(box1: list, box2: list) -> list:
    """
    Merge two bounding boxes in xyxy format (x1, y1, x2, y2) by calculating 
    the smallest box that can enclose both.
    Args:
        box1 (list): The first bounding box as [x1, y1, x2, y2].
        box2 (list): The second bounding box as [x1, y1, x2, y2].

    Returns:
        list: The merged bounding box in xyxy format.
    """
    x1 = min(box1[0], box2[0])
    y1 = min(box1[1], box2[1])
    x2 = max(box1[2], box2[2])
    y2 = max(box1[3], box2[3])

    return [x1, y1, x2, y2]

def process_bbox_20(bbox, image_size=(1920, 1080)):
    x1, y1, x2, y2 = bbox
    x1 = x1 * image_size[0] / 1920
    x2 = x2 * image_size[0] / 1920
    y1 = y1 * image_size[1] / 1080
    y2 = y2 * image_size[1] / 1080
    y1 = max(0,y1-4*(y2-y1))
    bbox = [int(x1), int(y1), int(x2), int(y2)]

    return bbox