from datetime import datetime
import os
import time
import json

from kafka import KafkaProducer
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from src.utils.file_processing import extract_video_duration_from_srs_config
from src.utils.helpers import get_video_start_end_datetime


def on_send_success(record_metadata):
    print("Send succeed")


def on_send_error(excp):
    print("Send error:", exc_info=excp)


class Handler(FileSystemEventHandler):
    def __init__(self, kafka_client, kafka_topic, video_duration):
        self.kafka_client = kafka_client
        self.kafka_topic = kafka_topic
        self.video_duration = video_duration

    @staticmethod
    def on_any_event(event):
        if event.event_type != "modified":
            print(
                "[{}] noticed: [{}] on: [{}] ".format(
                    time.asctime(), event.event_type, event.src_path
                )
            )

    def get_extra_information(self, video_url):
        camera_key = video_url.split("/")[-2].removesuffix(".flv")
        start_time, end_time = get_video_start_end_datetime(video_url, self.video_duration)
        return  {
            "camera_key": camera_key,
            "features": [],
            "models": [],
            "status": "new",
            "start_time": start_time,
            "end_time": end_time
        }


    def on_moved(self, event: FileSystemEvent) -> None:
        print(
            f"ON_MOVED -----> event type: {event.event_type}  src_path: {event.src_path}, des_path: {event.dest_path}"
        )
        # Create a JSON object to send to Kafka
        extra_information = self.get_extra_information(event.dest_path)
        message = {
            "video_url": event.dest_path,
            "extra_information": extra_information
        }
        self.kafka_client.send(
            self.kafka_topic, value=message
        ).add_callback(on_send_success).add_errback(on_send_error)


    # def on_created(self, event: FileSystemEvent) -> None:
    #     print(f'CREATE:----------------- event type: {event.event_type}  src_path: {event.src_path}')
    #     extra_information = self.get_extra_information(event.src_path)
    #     message = {
    #         "video_url": event.src_path,
    #         "extra_information": extra_information
    #     }
    #     self.kafka_client.send(self.kafka_topic, value=message).add_callback(on_send_success).add_errback(on_send_error)


class Watcher:
    def __init__(self, path, kafka_broker, kafka_topic) -> None:
        self.observer = Observer()
        self.path = path
        self.kafka_broker = kafka_broker
        self.kafka_topic = kafka_topic

        self.kafka_producer = KafkaProducer(
            bootstrap_servers=[self.kafka_broker], retries=5,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

        self.video_duration = extract_video_duration_from_srs_config(
            os.getenv("SRS_CONFIG_PATH", "/usr/srs_cfg/vms.conf")
        )

    def run(self):
        event_handler = Handler(self.kafka_producer, self.kafka_topic, self.video_duration)
        self.observer.schedule(event_handler, self.path, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except:
            self.observer.stop()
            print("Error")

        self.observer.join()


if __name__ == "__main__":
    print("***** Start Watchdog Service ******")
    kafka_broker = os.getenv("KAFKA_BROKER")
    kafka_topic = os.getenv("KAFKA_TOPIC_DVR")
    now_time = datetime.now().strftime("%d/%m/%y %H:%M:%S")
    print(f"Time: {now_time}")

    w = Watcher("/usr/dvr_videos", kafka_broker, kafka_topic)
    w.run()
