export APP_NAME="PAR02"
export KAFKA_DEEPSTREAM_TOPIC="emagic.par"

python fake-par02.py --model=yolov8n.pt \
    --video=/app/test_volumes/dvr_test_video/rainscale11.mp4 \
    --save_video_dir=/app/test_volumes/output \
    --cam_id=7297170438710103 \