import cv2
import imageio


writer = imageio.get_writer(
    "/app/test_volumes/output/convert_mp4.mp4",
    fps=60,
    codec="libx264",
    quality=3,
)
cap = cv2.VideoCapture("/app/test_volumes/dvr_test_video/rainscale11.mp4")
frame_id = 1
while cap.isOpened():
    print("frame_id", frame_id)
    ret, frame = cap.read()
    if not ret:
        break
    frame_id += 1
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_rs = cv2.resize(frame, (854, 480))
    writer.append_data(frame_rs)
    if frame_id > 1000:
        break
writer.close()
