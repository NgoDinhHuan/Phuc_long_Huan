#!/usr/bin/env python
import argparse
from src.repository.feature import get_cams_by_features
from src.models.input_data import InputData
import src.pipelines.org_triton_pipeline_par as org_pipeline
from datetime import datetime
import time
from kafka import KafkaConsumer
import os
import sys
import json

import logging

# Configure logging to output to the console
os.makedirs('/logs', exist_ok=True)
log_filename = f'/logs/{os.getenv("MODEL_NAME", default="log")}.log'
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()  # This sends logs to stdout
    ]
)

sys.path.append("../")


TEST = int(os.getenv("TEST", default=0))
BATCH_SIZE = int(os.getenv("BATCH_SIZE_PROCESS", default=1))
BATCH_TIME_SECOND = int(os.getenv("BATCH_TIME_SECOND", default=5))
TARGET_FEATURES = os.getenv("TARGET_FEATURES", default=[]).split(',')

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
        logging.error(f"Kafka Consumer from broker {kafka_broker} failed: {e}")
        return
    
    try:
        cs.subscribe([kafka_topic_dvr])
    except Exception as e:
        logging.error(f"Kafka subscribe to topic KAFKA_TOPIC_DVR failed: {e}")
        return


    input_data = InputData()
    target_cams = get_cams_by_features(TARGET_FEATURES)
    logging.info(f"Target cam: {target_cams}")

    batch_start_time = time.time()
    try:
        for message in cs:
            video_url = message.value.get("video_url")
            extra_information = message.value.get("extra_information")
            logging.info(video_url)

            # Skip file *.tmp
            if video_url.split(".")[-1] == "tmp":
                continue

            # Skip if file is not exist
            if not os.path.exists(video_url):
                logging.warning("File not exist: ", video_url)
                continue

            cam_id = video_url.split("/")[4]
            video_url = "file://" + video_url

            # Check which AI function we need to run for this cam id
            do_process = False
            if TARGET_FEATURES:
                if cam_id in target_cams:
                    do_process = True
            else:
                do_process = True

            pgie = 'nvinferserver-grpc'
            config = os.getenv('PGIE_CONFIG_FILE_PATH') #'/configs/pgies/forklift_person/config_infer_server_primary.txt'

            if do_process:
                input_data.add_source(uri_source=video_url, cam_id=cam_id, extra_information=extra_information)

                # Set start batch time
                if input_data.get_size() == 1:
                    batch_start_time = time.time()
                duration = time.time() - batch_start_time

                if input_data.get_size() >= BATCH_SIZE or duration >= BATCH_TIME_SECOND:
                    logging.info(f"******* Start pipeline {pipeline_name}*******")
                    now_time = datetime.now().strftime("%d/%m/%y %H:%M:%S")
                    logging.info(f"Time: {now_time}")

                    try:
                        start_time = time.time()
                        org_pipeline.run(input_data, pgie, config)
                        input_data.clean_source()
                        logging.info("Done!")
                        end_time = time.time()
                        elapsed_time = end_time - start_time
                        logging.info(f"Process time: {elapsed_time}")
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
    config = '/configs/pgies/forklift_person/config_infer_server_primary.txt'

    cnt = 0
    for message in range(BATCH_SIZE):
        video_url = videos[cnt]
        cnt+=1

        logging.info(video_url)

        # Skip if file is not exist
        if not os.path.exists(video_url):
            logging.warning("File not exist: ", video_url)
            continue

        video_url = "file://" + video_url

        cam_id='test'
        do_process = True

        if do_process:
            input_data.add_source(uri_source=video_url, cam_id=cam_id)
            if input_data.get_size() >= BATCH_SIZE:
                logging.info(f"******* Start pipeline {pipeline_name}*******")
                now_time = datetime.now().strftime("%d/%m/%y %H:%M:%S")
                logging.info(f"Time: {now_time}")

                try:
                    start_time = time.time()
                    org_pipeline.run(input_data, pgie, config)
                    input_data.clean_source()
                    logging.info("Done!")
                    end_time = time.time()
                    elapsed_time = end_time - start_time
                    logging.info(f"Process time: {elapsed_time}")
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
        logging.info(f"Start pipeline name: {args.name}!")
        pipeline_name = args.name

    try:
        while True:
            try:
                if TEST:
                    test(pipeline_name)
                else:
                    consumer(pipeline_name)
                
            except Exception as e:
                logging.error(f"Error: {e}")
                logging.info("Retry in 5 second")
    except InterruptedError:
        exit()
