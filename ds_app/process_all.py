#!/usr/bin/env python
import argparse
from src.repository.feature import get_cams_by_features
from src.models.input_data import InputData
from src.pipelines.dsl_pipeline import DSL_Pipeline
from src.pipelines.dsl_pipeline_par import DSL_Pipeline_PAR
from datetime import datetime
import time
from kafka import KafkaConsumer
import os
from dsl.dsl import *
import sys
from collections import namedtuple

import logging

# Configure logging to output to the console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # This sends logs to stdout
        logging.FileHandler("app.log"),
    ],
)

sys.path.append("../")


BATCH_SIZE = int(os.getenv("BATCH_SIZE_PROCESS", default=1))
track_config_path = os.getenv("TRACK_CONFIG_FILE_PATH")

GROUP_ALCOHOL = ["OTH02"]
GROUP_WAREHOUSE = [
    "MHE01",
    "MHE02",
    "MHE03",
    "MHE04",
    "HM01",
    "HM02",
    "HM04",
    "HM05",
    "HM07",
    "PL01",
    "PL02",
    "PL03",
    "VEH01",
]
GROUP_CLASSIFICATION = ["PAR01", "PAR02"]

Group = namedtuple(
    "Group", ["feature", "pgie_config_path", "sgie_config_path", "kafka_topic"]
)
groups = [
    Group(
        GROUP_ALCOHOL,
        "configs/pgies/yolov8_alcoholxperson/config_infer_primary_yoloV8.txt",
        "",
        "emagic.alcohol_person",
    ),
    Group(
        GROUP_WAREHOUSE,
        "configs/pgies/yolov8m_warehouse/config_infer_primary_yoloV8.txt",
        "",
        "emagic.warehouse",
    ),
    Group(
        GROUP_CLASSIFICATION,
        "configs/pgies/yolov8/config_infer_primary_yoloV8.txt",
        "configs/sgies/par/config_infer_sgie.txt",
        "emagic.par",
    ),
]


class GroupFeatures:
    target_features: list
    target_cams: list
    input_src: InputData
    pgie_config_path: str
    sgie_config_path: str
    kafka_topic: str

    def __init__(
        self,
        target_features: list = [],
        pgie_config_path: str = "",
        sgie_config_path: str = [],
        kafka_topic: str = "",
    ) -> None:
        self.target_features = target_features
        self.input_src = InputData()
        self.pgie_config_path = pgie_config_path
        self.sgie_config_path = sgie_config_path
        self.kafka_topic = kafka_topic

    def getTargetFeatures(self) -> list:
        return self.target_features

    def getInputSrc(self) -> list:
        return self.input_src

    def addCam(self, camid: str):
        self.target_cams.append(camid)


def consumer(pipeline_name):
    kafka_broker = os.getenv("KAFKA_BROKER")
    kafka_topic_dvr = os.getenv("KAFKA_TOPIC_DVR")
    try:
        cs = KafkaConsumer(
            bootstrap_servers=[kafka_broker],
            auto_offset_reset="latest",
        )
    except Exception as e:
        logging.error(f"Kafka Consumer from broker {kafka_broker} failed: {e}")
        return

    try:
        cs.subscribe([kafka_topic_dvr])
    except Exception as e:
        logging.error(f"Kafka subscribe to topic KAFKA_TOPIC_DVR failed: {e}")
        return

    list_group_features = []
    for g in groups:
        group_features = GroupFeatures(
            target_features=g.feature,
            pgie_config_path=g.pgie_config_path,
            sgie_config_path=g.sgie_config_path,
            kafka_topic=g.kafka_topic,
        )
        list_group_features.append(group_features)

    # Get all cam and features
    for idx, f in enumerate(list_group_features):
        target_cams = get_cams_by_features(f.target_features)
        f.target_cams = target_cams
        logging.info(f"Feature:{f.target_features} ---> Cam:{f.target_cams}")

    try:
        for message in cs:
            message = message.value.decode("utf-8")
            video_url = message

            test = False
            if test:
                video_url = "/opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h265.mp4"  # for test
                cam_id = "7297170438710103"  ## for test
            else:
                # Skip file *.tmp
                if video_url.split(".")[-1] == "tmp":
                    continue

                # Skip if file is not exist
                if not os.path.exists(video_url):
                    logging.warning("File not exist: ", video_url)
                    continue

                # Extract cam id
                cam_id = video_url.split("/")[4]

            logging.info(video_url)
            logging.info(f"cam_id: {cam_id}")

            # Get all cam and features
            for f in list_group_features:
                if cam_id in f.target_cams:
                    logging.info(
                        f"Add source {video_url} into {f.target_features}"
                    )
                    f.input_src.add_source(uri_source=video_url, cam_id=cam_id)
                    if f.input_src.get_size() >= BATCH_SIZE:
                        ds_process(
                            f.input_src,
                            pgie_config_file=f.pgie_config_path,
                            sgie_config_file=f.sgie_config_path,
                            kafka_topic=f.kafka_topic,
                            pipeline_name=pipeline_name,
                        )

    finally:
        cs.close()


def ds_process(
    input_data: InputData,
    pgie_config_file: str,
    kafka_topic: str,
    sgie_config_file: str = "",
    pipeline_name: str = "pipeline_all",
):
    logging.info(f"******* Start pipeline {pipeline_name}*******")
    now_time = datetime.now().strftime("%d/%m/%y %H:%M:%S")
    logging.info(f"Time: {now_time}")

    os.environ["KAFKA_DEEPSTREAM_TOPIC"] = kafka_topic

    if not sgie_config_file:
        pipeline = DSL_Pipeline(
            input_srcs=input_data.uri_sources,
            cam_ids=input_data.cam_ids,
            pgie_infer_config_file=pgie_config_file,
            tracker_config_file=track_config_path,
            pipeline_name=pipeline_name,
        )
    else:
        pipeline = DSL_Pipeline_PAR(
            input_srcs=input_data.uri_sources,
            cam_ids=input_data.cam_ids,
            pgie_infer_config_file=pgie_config_file,
            sgie_infer_config_file=sgie_config_file,
            tracker_config_file=track_config_path,
            pipeline_name=pipeline_name,
        )

    try:
        error = pipeline.run()
        if error:
            logging.info("Has error, exit")
            exit(1)
        input_data.clean_source()
        logging.info("Done!")
        # time.sleep(5)
    except Exception as e:
        logging.error(e)
        exit(1)


if __name__ == "__main__":
    # Initialize the parser
    parser = argparse.ArgumentParser(description="")

    # Add arguments
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        required=True,
        help="The name of the pipeline.",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Use the arguments
    pipeline_name = ""
    if args.name:
        logging.info(f"Start pipeline name: {args.name}!")
        pipeline_name = args.name

    try:
        while True:
            try:
                consumer(pipeline_name)
            except Exception as e:
                logging.error(f"Error: {e}")
                logging.info("Retry in 5 second")
            time.sleep(5)
    except InterruptedError:
        exit()
