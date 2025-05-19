#!/usr/bin/env python
import argparse
from src.repository.feature import get_feature_cameras_mapping, get_ds_topic_cameras_mapping, get_model_ai_features_mapping
from src.models.input_data import InputData
from src.pipelines.org_triton_new_pipeline import DSL_Pipeline
from datetime import datetime
import time
from kafka import KafkaConsumer
import os
import sys
import json
from utils.memory import is_memory_exceeded
from utils.helpers import restart_container
from utils.check_gpu import check_gpu_memory
from loguru import logger

# Configure logging to output to the console
os.makedirs('/logs', exist_ok=True)

logger.add(f'/logs/{os.getenv("MODEL_NAME", default="deepstream")}' + '_{time:YYYY-MM-DD}.log',
           format="{time} {level} {message}",
           level="INFO",
           rotation="00:00",  # split log file at midnight
           retention="30 days",  # keep log file for 30 days
           enqueue=True
           )

sys.path.append("../")

TEST = int(os.getenv("TEST", default=0))
BATCH_SIZE = int(os.getenv("BATCH_SIZE_PROCESS", default=1))
BATCH_TIME_SECOND = int(os.getenv("BATCH_TIME_SECOND", default=5))


def consumer(pipeline_name):
    kafka_broker = os.getenv("KAFKA_BROKER")
    kafka_topic_dvr = os.getenv("KAFKA_TOPIC_DVR")
    try:
        cs = KafkaConsumer(
            bootstrap_servers=[kafka_broker],
            auto_offset_reset="latest",
            value_deserializer=lambda v: json.loads(v.decode('utf-8'))
        )
    except Exception as e:
        logger.error(f"Kafka Consumer from broker {kafka_broker} failed: {e}")
        return

    try:
        cs.subscribe([kafka_topic_dvr])
    except Exception as e:
        logger.error(f"Kafka subscribe to topic KAFKA_TOPIC_DVR failed: {e}")
        return

    ai_models_mapping = get_model_ai_features_mapping(except_model=["ds_product_fall","ds_alcohol_person"])
    all_features = set(value for values in ai_models_mapping.values() for value in values)
    feature_cameras_mapping = get_feature_cameras_mapping(all_features)
    camera_topics_mapping = get_ds_topic_cameras_mapping(ai_models_mapping, feature_cameras_mapping)
    print(camera_topics_mapping)
    print("all_features",all_features)

    input_data = InputData()
    batch_start_time = time.time()
    try:
        for message in cs:
            video_url = message.value.get("video_url")
            extra_information = message.value.get("extra_information")
            logger.info(video_url)

            # Skip file *.tmp
            if video_url.split(".")[-1] == "tmp":
                continue

            # Skip if file is not exist
            if not os.path.exists(video_url):
                logger.warning("File not exist: ", video_url)
                continue

            cam_id = extra_information.get("camera_key")
            video_url = "file://" + video_url

            # Check which AI function we need to run for this cam id
            do_process = True


            if do_process:
                input_data.add_source(uri_source=video_url, cam_id=cam_id, extra_information=extra_information)

                # Set start batch time
                if input_data.get_size() == 1:
                    batch_start_time = time.time()
                duration = time.time() - batch_start_time

                if input_data.get_size() >= BATCH_SIZE  or duration >= BATCH_TIME_SECOND:
                    logger.info(f"******* Start pipeline {pipeline_name}*******")
                    now_time = datetime.now().strftime("%d/%m/%y %H:%M:%S")
                    logger.info(f"Time: {now_time}")
                    pipeline = DSL_Pipeline(
                        input_srcs=input_data.get_src(),
                        cam_ids=input_data.get_cams_id(),
                        number_branches=2,
                        pgie_config_file_paths=[
                                                "/configs/pgies/yolov8m_warehouse/config_infer_server_primary_yolov8m_warehouse.txt",
                                                # "/configs/pgies/yolov8m_warehouse/config_infer_server_primary_yolov8m_warehouse_ppe02.txt",
                                                "/configs/pgies/yolov8m_warehouse/config_infer_server_primary_yolov8m_warehouse_par.txt",
                                                 ],
                        sgie_config_file_paths=[
                                                None,
                                                # "/configs/sgies/ppe02/config_infer_server_primary.txt",
                                                "/configs/sgies/par/config_infer_server_primary.txt"

                                                 ],
                        sgie_rule_names =[None,"par"],
                        model_topic_mappings=[
                            "ds_warehouse",
                            # "ds_ppe02",
                            "ds_par"
                        ],
                        kafka_topics = [
                            "emagic.warehouse",
                            # "emagic.ppe02",
                            "emagic.par"
                        ],
                        camera_topics_mapping=camera_topics_mapping,
                        model_id_mapping=[103,104],
                        target_class_names_dict={
                            # "ds_ppe02": ["person"],
                            "ds_par": ["person", "person_visible_clothes", "person_use_phone", "Person_eat_drink",
                                       "person_carry_object", "person_pull_object"],
                            },
                        pipeline_name=pipeline_name
                    )

                    try:
                        check_gpu = check_gpu_memory(device=0, batch_size=BATCH_SIZE, decode_image=100)
                        if check_gpu:
                            start_time = time.time()
                            pipeline.run_pipeline(input_data)
                            logger.info("Done!")
                            end_time = time.time()
                            elapsed_time = end_time - start_time
                            logger.info(f"Process time: {elapsed_time}")
                        input_data.clean_source()
                        logger.info("Done!")
                        end_time = time.time()
                        elapsed_time = end_time - start_time
                        logger.info(f"Process time: {elapsed_time}")
                        # check ram cpu if exceeded we need restart
                        try:
                            if is_memory_exceeded(threshold=0.8):
                                cs.close()
                                restart_container()
                        except Exception as e:
                            logger.error(f"{str(e)}")
                    except Exception as e:
                        print(e)

    finally:
        cs.close()


def test(pipeline_name):
    input_data = InputData()

    videos = [
        '/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h265.mp4',
        '/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h265.mp4',
        '/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h265.mp4',
        '/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h265.mp4',
        '/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h265.mp4',
        '/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h265.mp4',
        '/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h265.mp4',
        '/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h265.mp4'
    ]
    BATCH_SIZE = len(videos)


    cnt = 0
    for message in range(BATCH_SIZE):
        video_url = videos[cnt]
        cnt += 1

        logger.info(video_url)

        # Skip if file is not exist
        if not os.path.exists(video_url):
            logger.warning("File not exist: ", video_url)
            continue

        video_url = "file://" + video_url

        cam_id = 'test'
        do_process = True

        if do_process:
            input_data.add_source(uri_source=video_url, cam_id=cam_id)
            # Set start batch time
            if input_data.get_size() == 1:
                batch_start_time = time.time()
            duration = time.time() - batch_start_time
            if input_data.get_size() >= BATCH_SIZE or duration >= BATCH_TIME_SECOND:
                logger.info(f"******* Start pipeline {pipeline_name}*******")
                now_time = datetime.now().strftime("%d/%m/%y %H:%M:%S")
                logger.info(f"Time: {now_time}")
                pipeline = DSL_Pipeline(
                    input_srcs=input_data.get_src(),
                    cam_ids=input_data.get_cams_id(),
                    number_branches=4,
                    pgie_config_file_paths=[
                        "/configs/pgies/yolov8m/config_infer_server_primary.txt",
                        "/configs/pgies/forklift_person/config_infer_server_primary.txt",
                        "/configs/pgies/yolov8m_ppe02/config_infer_server_primary.txt",
                        "/configs/pgies/yolov8m/config_infer_server_primary.txt"
                    ],
                    sgie_config_file_paths=[
                        None,
                        None,
                        "/configs/sgies/ppe02/config_infer_server_primary.txt",
                        "/configs/sgies/par/config_infer_server_primary.txt"

                    ],
                    sgie_rule_names=[None, None, "ppe02", "par"],
                    model_topic_mappings=[
                        "ds_yolov8m",
                        "ds_forklift_product",
                        "ds_par",
                        "ds_ppe02"
                    ],
                    camera_topics_mapping=camera_topics_mapping,
                    target_class_names_dict={},
                    kafka_topic_prefix="emagic",
                    pipeline_name=pipeline_name
                )

                try:
                    start_time = time.time()
                    pipeline.run_pipeline(input_data)
                    input_data.clean_source()
                    logger.info("Done!")
                    end_time = time.time()
                    elapsed_time = end_time - start_time
                    logger.info(f"Process time: {elapsed_time}")
                except Exception as e:
                    print(e)


if __name__ == "__main__":
    # Initialize the parser
    parser = argparse.ArgumentParser(description="")

    # Add arguments
    parser.add_argument("-n", "--name", type=str, required=True, help="The name of the pipeline.")

    # Parse the arguments
    args = parser.parse_args()
    # get camera config

    # Use the arguments
    pipeline_name = ''
    if args.name:
        logger.info(f"Start pipeline name: {args.name}!")
        pipeline_name = args.name

    try:
        while True:
            try:
                if TEST:
                    test(pipeline_name)
                else:
                    consumer(pipeline_name)

            except Exception as e:
                logger.error(f"Error: {e}")
                logger.info("Retry in 5 second")
    except InterruptedError:
        exit()