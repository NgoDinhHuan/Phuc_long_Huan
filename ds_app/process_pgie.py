#!/usr/bin/env python
import argparse
from src.repository.feature import get_cams_by_features
from src.models.input_data import InputData
import src.pipelines.org_triton_pipeline as org_pipeline
from datetime import datetime
import time
from kafka import KafkaConsumer
import os
import sys
import json

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
TARGET_FEATURES = os.getenv("TARGET_FEATURES", default=[]).split(',')

def consumer(pipeline_name):
    logger.info("=======================")
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


    input_data = InputData()
    target_cams = get_cams_by_features(TARGET_FEATURES)
    logger.info(f"Target cam: {target_cams}")

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
            do_process = False
            if TARGET_FEATURES:
                if cam_id in target_cams:
                    do_process = True
            else:
                do_process = True

            if do_process:
                input_data.add_source(uri_source=video_url, cam_id=cam_id, extra_information=extra_information)

                # Set start batch time
                if input_data.get_size() == 1:
                    batch_start_time = time.time()
                duration = time.time() - batch_start_time

                if input_data.get_size() >= BATCH_SIZE or duration >= BATCH_TIME_SECOND:
                    logger.info(f"******* Start pipeline {pipeline_name}*******")
                    now_time = datetime.now().strftime("%d/%m/%y %H:%M:%S")
                    logger.info(f"Time: {now_time}")

                    try:
                        start_time = time.time()
                        org_pipeline.run(input_data, 'nvinferserver-grpc')
                        input_data.clean_source()
                        logger.info("Done!")
                        end_time = time.time()
                        elapsed_time = end_time - start_time
                        logger.info(f"Process time: {elapsed_time}")
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

    pgie = 'nvinferserver-grpc'

    cnt = 0
    for message in range(BATCH_SIZE):
        video_url = videos[cnt]
        cnt+=1

        logger.info(video_url)

        # Skip if file is not exist
        if not os.path.exists(video_url):
            logger.warning("File not exist: ", video_url)
            continue

        video_url = "file://" + video_url

        cam_id='test'
        do_process = True

        if do_process:
            input_data.add_source(uri_source=video_url, cam_id=cam_id)
            if input_data.get_size() >= BATCH_SIZE:
                logger.info(f"******* Start pipeline {pipeline_name}*******")
                now_time = datetime.now().strftime("%d/%m/%y %H:%M:%S")
                logger.info(f"Time: {now_time}")

                try:
                    start_time = time.time()
                    org_pipeline.run(input_data, pgie)
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
