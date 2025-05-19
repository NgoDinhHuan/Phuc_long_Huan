export APP_NAME="HM05"
export CLOUD_IMAGE="emagiceye-cloud-app:v2" ## change supervision to 0.21.0
export TARGET='/hdd1/dannv5/.deploy/${{github.repository}}'
export DATABASE_URL='postgresql://eme_db:48554f2d6defd93cb67b392acc1256c11fbe114b927b6e7dbd22a8053d76df2f@192.168.1.92:51001/postgres?sslmode=disable'
export KAFKA_BROKER='47.128.81.230:8003'
export KAFKA_VEHICLE_TOPIC='emagic.vehicles'
export KAFKA_EVENT_TOPIC='emagic.events'
export KAFKA_EVIDENCE_TOPIC='emagic.evidences'
export STORAGE_URL='192.168.1.92:51003'
export STORAGE_DOMAIN_URL='https://minio.emagiceyes.rainscales.com'
export STORAGE_BUCKET='emagic-event'
export STORAGE_ACCESS_KEY='eme_minio'
export STORAGE_SECRET_KEY='Rainscales@2024'
export STORAGE_SECURE=false
export LLAVA_URL='http://192.168.1.91:8080/videos/chat'
export KAFKA_DEEPSTREAM_TOPIC='emagic.deepstream.par02'
export KAFKA_PRODUCT_TOPIC='emagic.products'

python fake-hm05.py --model=/home/duongpd/trungnt/MGE/mge_ai_cloud/test_volumes/model_weights/detect/yolov8m_warehouse.pt \
    --video=/home/duongpd/trungnt/MGE/mge_ai_cloud/test_volumes/output/hm05_1.mp4 \
    --save_video_dir=/home/duongpd/trungnt/MGE/mge_ai_cloud/test_volumes/output \
    --cam_id=7297170438710103 \
    --mounted_save_dir=/usr/dvr_videos ## use when save dir is mounted into docker-compose
