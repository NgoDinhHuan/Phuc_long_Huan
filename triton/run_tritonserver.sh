#!/bin/bash

# Configurations
BASE_DIR="/app/models"
TRTEXEC="/usr/src/tensorrt/bin/trtexec"
GRPC_POOL_SIZE=88
models_to_rebuild=() # List of models to rebuild. eg ("yolov8m_trt" "forklift_product_trt")

declare -A models=(
  ["par_2609"]="par_2609_dynamic_shape.onnx"
  ["yolov8m_warehouse_trt"]="yolov8m_warehouse_v2_t12.onnx"
)

declare -A model_options=(
  ["par_2609"]="--fp16 --minShapes='input':1x3x256x192 --optShapes='input':32x3x256x192 --maxShapes='input':64x3x256x192"
  ["yolov8m_warehouse_trt"]="--fp16 --minShapes='input':1x3x640x640 --optShapes='input':64x3x640x640 --maxShapes='input':128x3x640x640"
)

declare -A deploy_versions=(
  ["par_2609"]="2"
  ["yolov8m_warehouse_trt"]="3"
)

# Function to download ONNX models
download_model() {
  local model_folder=$1
  local onnx_filename=$2
  local version=$3
  local save_folder="$BASE_DIR/$model_folder/$version"
  local onnx_path="$save_folder/model.onnx"

  mkdir -p "$save_folder"

  if [ ! -f "$onnx_path" ]; then
    echo "Downloading $onnx_filename to $onnx_path..."
    wget -q "$BASE_URL/$onnx_filename" -O "$onnx_path"
    sleep 1
    if [ ! -s "$onnx_path" ]; then
      echo "Error: Downloaded file is empty. Retrying..."
      rm "$onnx_path"
      echo "download URL : $BASE_URL/$onnx_filename"
      wget -q "$BASE_URL/$onnx_filename" -O "$onnx_path"
    fi
  else
    echo "$onnx_path already exists, skipping download."
  fi

  local file_size=$(stat -c%s "$onnx_path")
  echo "Size of $onnx_path: $file_size bytes"
}

# Function to remove TensorRT plan file
remove_plan() {
  local model_folder=$1
  local version=$2
  local plan_path="$BASE_DIR/$model_folder/$version/model.plan"

  if [ -f "$plan_path" ]; then
    echo "Removing plan file for $model_folder version $version..."
    rm "$plan_path"
  else
    echo "No plan file found for $model_folder version $version."
  fi
}

# Function to generate TensorRT plan file
generate_plan() {
  local model_folder=$1
  local version=$2
  local onnx_path="$BASE_DIR/$model_folder/$version/model.onnx"
  local plan_path="$BASE_DIR/$model_folder/$version/model.plan"
  local options=$3

  mkdir -p "$BASE_DIR/$model_folder/$version"

  if [ ! -f "$plan_path" ]; then
    echo "Generating plan file for $model_folder version $version..."
    $TRTEXEC --onnx="$onnx_path" $options --saveEngine="$plan_path"
  else
    echo "Plan file already exists for $model_folder version $version."
  fi
}

# Download ONNX models for each version in deploy_versions
echo "Starting model download..."
for model_folder in "${!models[@]}"; do
  versions="${deploy_versions[$model_folder]}"
  for version in $versions; do
    download_model "$model_folder" "${models[$model_folder]}" "$version"
  done
done

# Remove specified plan files
echo "Removing specified plan files..."
for model_folder in "${models_to_rebuild[@]}"; do
  versions="${deploy_versions[$model_folder]}"
  for version in $versions; do
    remove_plan "$model_folder" "$version"
  done
done

# Convert ONNX models to TensorRT plans for each version in deploy_versions
echo "Starting model conversion..."
for model_folder in "${!models[@]}"; do
  versions="${deploy_versions[$model_folder]}"
  for version in $versions; do
    onnx_path="$BASE_DIR/$model_folder/$version/model.onnx"
    if [ -f "$onnx_path" ]; then
      generate_plan "$model_folder" "$version" "${model_options[$model_folder]}"
    else
      echo "ONNX file not found for $model_folder version $version, skipping conversion."
    fi
  done
done

# Start Triton server
echo "Starting Triton server..."
tritonserver --model-repository=$BASE_DIR --log-info=1 --log-warning=1 --log-error=1 --grpc-infer-allocation-pool-size=$GRPC_POOL_SIZE
