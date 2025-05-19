# Deployment
### Build docker image
` docker build -t mge_ai . `

### Run docker compose
` docker compose up `

# Quantize Model
## Convert yoloV8.pt to yoloV8.onnx
- Ultralytics

` git clone https://github.com/ultralytics/ultralytics `

- Deepstream Yolo

` git clone https://github.com/marcoslucianops/DeepStream-Yolo `

- Copy file:

` cp DeepStream-Yolo/utils/export_yoloV8.py ultralytics/ `

- Download model

` cd ultralytics && wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt `

- Convert:

` docker pull ultralytics/ultralytics:latest `

` docker run --rm -it -v ./:/ws -w /ws ultralytics/ultralytics:latest ` 

` python3 export_yoloV8.py -w yolov8s.pt --dynamic `

## Convert ONNX model to tensorrt .engine
` /usr/src/tensorrt/bin/trtexec --onnx=[file] --fp16 --saveEngine=[file] `

# Testing
### Create RTSP stream from video
- run simple rtsp server:
  
`docker run --rm -it -e RTSP_PROTOCOLS=tcp -p 8554:8554 aler9/rtsp-simple-server `
- stream video to rtsp:

`ffmpeg -re -stream_loop -1 -i 1.mp4 -vcodec h264 -f rtsp rtsp://localhost:8554/mystream `
- play:

`ffplay rtsp://localhost:8554/mystream `