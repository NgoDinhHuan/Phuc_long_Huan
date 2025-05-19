#!/bin/bash

MINIO_URL="https://minio.emagiceyes.rainscales.com/cloud-ai-models/infer/third_party_model/model.pkl"
WEIGHT_PATH="/app/model.pkl"

# Nếu model chưa tồn tại, tải xuống
if [ ! -f "$WEIGHT_PATH" ]; then
    echo "Downloading model from MinIO..."
    wget "$MINIO_URL" -O "$WEIGHT_PATH"

    # Kiểm tra xem tải về có thành công không
    if [ ! -f "$WEIGHT_PATH" ]; then
        echo "Failed to download the weight file"
        exit 1
    fi
else
    echo "Model already exists. Skipping download."
fi
