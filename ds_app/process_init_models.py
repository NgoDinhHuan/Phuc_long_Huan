#!/usr/bin/env python
from src.models.input_data import InputData
from src.pipelines.dsl_pipeline_par import DSL_Pipeline_PAR
from src.pipelines.dsl_pipeline import DSL_Pipeline
from datetime import datetime
import time
import os
import sys
import shutil

sys.path.append("../")

BATCH_SIZE = int(os.getenv("BATCH_SIZE_PROCESS", default=1))

track_config_path = os.getenv("TRACK_CONFIG_FILE_PATH")


def extract_infer_values(file_path):
    gpu_id = None
    network_mode = None
    model_engine_file_name = None
    onnx_file = None

    with open(file_path, "r") as file:
        for line in file:
            if line.startswith("gpu-id="):
                gpu_id = int(line.split("=")[1].strip())
            elif line.startswith("network-mode="):
                network_mode = int(line.split("=")[1].strip())
            elif line.startswith("model-engine-file="):
                model_engine_file_name = line.split("=")[1].strip()
            elif line.startswith("onnx-file="):
                onnx_file = line.split("=")[1].strip()

    network_type = "fp32"
    if network_mode == 0:
        network_type = "fp32"
    elif network_mode == 1:
        network_type = "int8"
    else:
        network_type = "fp16"

    return gpu_id, network_type, model_engine_file_name, onnx_file


def rename_file(old_name, new_name):
    os.rename(old_name, new_name)
    print(f"Change file renamed from {old_name} to {new_name}")


def move_file(old_path, new_directory):
    if os.path.exists(old_path):
        # Ensure the new directory exists
        if not os.path.exists(new_directory):
            os.makedirs(new_directory)

        # Construct the new path
        new_path = os.path.join(new_directory, os.path.basename(old_path))

        # Move the file
        shutil.move(old_path, new_path)
        print(f"File moved from {old_path} to {new_path}")
    else:
        print(f"File {old_path} does not exist")


def build():
    input_data = InputData()

    while input_data.get_size() < BATCH_SIZE:
        input_data.add_source(
            uri_source="/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h265.mp4",
            cam_id="test",
        )

    par_pipeline(
        input_data,
        os.getenv("PAR_PGIE_CONFIG_FILE_PATH"),
        os.getenv("PAR_SGIE_CONFIG_FILE_PATH"),
    )
    time.sleep(1)
    pgie_pipeline(input_data, os.getenv("ALCOHOL_PGIE_CONFIG_FILE_PATH"))
    time.sleep(1)
    pgie_pipeline(input_data, os.getenv("PPE_PGIE_CONFIG_FILE_PATH"))
    time.sleep(1)
    pgie_pipeline(input_data, os.getenv("WAREHOUSE_CONFIG_FILE_PATH"))
    time.sleep(1)
    pgie_pipeline(input_data, os.getenv("PPE02_PGIE_CONFIG_FILE_PATH"))
    time.sleep(1)
    pgie_pipeline(input_data, os.getenv("PRODUCT_FALL_PGIE_CONFIG_FILE_PATH"))
    time.sleep(1)
    pgie_pipeline(input_data, os.getenv("21LABEL7_CONFIG_FILE_PATH"))


def par_pipeline(input_data, pgie_config, sgie_config):
    print("******* Start PAR pipeline *******")
    now_time = datetime.now().strftime("%d/%m/%y %H:%M:%S")
    print(f"Time: {now_time}")
    pipeline = DSL_Pipeline_PAR(
        input_srcs=input_data.uri_sources,
        cam_ids=input_data.cam_ids,
        pgie_infer_config_file=pgie_config,
        sgie_infer_config_file=sgie_config,
        tracker_config_file=track_config_path,
    )
    pipeline.run()
    # change model .engine name
    # pgie
    gpu_id, network_type, model_engine_file_name, _ = extract_infer_values(
        pgie_config
    )
    model_name = f"model_b{BATCH_SIZE}_gpu{gpu_id}_{network_type}.engine"
    if os.path.exists(model_name):
        new_name = f"{model_engine_file_name.split('/')[-1]}"
        print(f"move {model_name} to {model_engine_file_name}")
        rename_file(model_name, new_name)

        new_dir = os.path.dirname(model_engine_file_name)
        print(f"move {new_name} to {new_dir}")
        move_file(new_name, new_dir)

    # sgie
    gpu_id, network_type, model_engine_file_name, onnx_file = (
        extract_infer_values(sgie_config)
    )
    model_name = f"{onnx_file}_b{BATCH_SIZE}_gpu{gpu_id}_{network_type}.engine"
    if os.path.exists(model_name):
        new_name = f"{model_engine_file_name.split('/')[-1]}"
        print(f"rename cur name: {model_name} to {new_name}")
        rename_file(model_name, new_name)

        new_dir = os.path.dirname(model_engine_file_name)
        print(f"move {new_name} to {new_dir}")
        move_file(new_name, new_dir)


def pgie_pipeline(input_data, pgie_config):
    print("******* Start Pgie pipeline *******")
    now_time = datetime.now().strftime("%d/%m/%y %H:%M:%S")
    print(f"Time: {now_time}")
    pipeline = DSL_Pipeline(
        input_srcs=input_data.uri_sources,
        cam_ids=input_data.cam_ids,
        pgie_infer_config_file=pgie_config,
        tracker_config_file=track_config_path,
    )
    pipeline.run()
    # change model .engine name
    # pgie
    gpu_id, network_type, model_engine_file_name, _ = extract_infer_values(
        pgie_config
    )
    model_name = f"model_b{BATCH_SIZE}_gpu{gpu_id}_{network_type}.engine"
    if os.path.exists(model_name):
        # rename_file(model_name, model_engine_file_name)
        new_name = f"{model_engine_file_name.split('/')[-1]}"
        print(f"move {model_name} to {model_engine_file_name}")
        rename_file(model_name, new_name)

        new_dir = os.path.dirname(model_engine_file_name)
        print(f"move {new_name} to {new_dir}")
        move_file(new_name, new_dir)


if __name__ == "__main__":
    try:
        build()
    except InterruptedError:
        exit()
