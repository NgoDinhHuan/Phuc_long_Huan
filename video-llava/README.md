
# Video-llava

#### 1. Running as a webservice

- Start the web service

```bash
# On Docker
docker build -t kairos-video-llava .
docker run -d --gpus all -p 8080:8080 kairos-video-llava
```

- Start with docker compose

```
docker compose up --build -d
```

- Invoke VideoLlava :

```bash
curl -X 'POST' \
  'http://localhost:8080/videos/chat?query=summary%20video' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@<filename>;type=video/mp4'
```
