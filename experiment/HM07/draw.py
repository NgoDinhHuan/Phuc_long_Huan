import cv2


def draw_bb(img, box, color, label):
    x1, y1, x2, y2 = list(map(int, box))
    len_h = int(0.2 * (y2 - y1))
    len_w = int(0.2 * (x2 - x1))
    line_tn = 2
    cv2.line(img, (x1, y1), (x1 + len_w, y1), color, line_tn)
    cv2.line(img, (x1, y1), (x1, y1 + len_h), color, line_tn)

    cv2.line(img, (x2, y2), (x2 - len_w, y2), color, line_tn)
    cv2.line(img, (x2, y2), (x2, y2 - len_h), color, line_tn)

    cv2.line(img, (x1, y2), (x1 + len_w, y2), color, line_tn)
    cv2.line(img, (x1, y2), (x1, y2 - len_h), color, line_tn)

    cv2.line(img, (x2, y1), (x2 - len_w, y1), color, line_tn)
    cv2.line(img, (x2, y1), (x2, y1 + len_h), color, line_tn)
    top_center = (int((x1 + x2) / 2), y1)
    text_point = (top_center[0] + len_h, top_center[1] - len_h)
    cv2.circle(img, top_center, radius=2, color=color, thickness=-1)

    cv2.line(img, top_center, text_point, color=color, thickness=1)
    cv2.line(img, text_point, (text_point[0] + (y2 - y1), text_point[1]), color=color, thickness=1)
    cv2.putText(img, label, (text_point[0], text_point[1] - 5), 1, 1, color, thickness=2, lineType=cv2.LINE_AA)
    overlay = img.copy()
    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color=(0, 0, 255), thickness=-1)
    alpha = 0.8  # Transparency factor.
    # Following line overlays transparent rectangle
    # over the image
    img_new = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)
    return img_new
