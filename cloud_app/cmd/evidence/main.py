import asyncio
import json
import os
import shutil
import time
from uuid import uuid4
import numpy as np
import cv2
import faust
import imageio
from loguru import logger
import gc
import psutil

from cloud_app.cmd.evidence.helpers import (init_save_paths,
                                            convert_timestamp_to_datetime,
                                            delete_folder_with_exclusions,
                                            check_exist_and_wait_for_files,
                                            post_to_event_collector)
from cloud_app.cmd.evidence.verify import verify_event_by_llava
from cloud_app.common.config import cfg
from cloud_app.gateway.contract.kafka import init_kafka_producer
from cloud_app.gateway.contract.minio import minio_client
from cloud_app.internal.controller.base.event import BaseEvent
from cloud_app.internal.pkg.box import (
    draw_bb,
    get_union_box, extend_bbox,
)

logger.add(f'/logs/{cfg.app_name}' + '_{time:YYYY-MM-DD}.log',
           format="{time} {level} {message}",
           level="INFO",
           rotation="00:00",  # split log file at midnight
           retention="30 days",  # keep log file for 30 days
           enqueue=True
           )
logger.info(f"Start {cfg.app_name} service")

logger.add(f'/logs/{cfg.app_name}_videos' + '_{time:YYYY-MM-DD}.log',
           format="{time} {level} {message}",
           retention="30 days",  # keep log file for 30 days
           enqueue=True,
           filter=lambda record: "evidence_videos" in record["extra"]
           )

app = faust.App(
    cfg.app_name,
    broker=cfg.kafka_broker,
    consumer_auto_offset_reset="latest")

app.conf.broker_max_poll_interval = 3000
app.conf.broker_max_poll_records = 3
app.conf.stream_processing_timeout = 3000
app.conf.broker_request_timeout = 400.0  #
app.conf.broker_session_timeout = 360  # time for waiting for broker response (heartbeat)
app.conf.broker_heartbeat_interval = 120  # time for sending heartbeat to broker
app.conf.broker_commit_livelock_soft_timeout = 600  # max time for waiting for broker response (commit)
# app.conf.consumer_group_instance_id = cfg.app_name


consume_topic = app.topic(cfg.kafka_evidence_topic, value_type=bytes)

kafka_producer = init_kafka_producer(cfg.event_kafka_broker)

connect_minio = minio_client.init()
if not connect_minio:
    logger.warning("Could not connect to Minio, will try later")


ENV_CONFIG = {"PRODUCTION": {"keep_evidence": True},
              "STAGING": {"keep_evidence": True},
              "DEVELOP": {"keep_evidence": True},
              "TEST": {"keep_evidence": True}}

REMOVE_EVIDENCE = not ENV_CONFIG[cfg.deploy_env]["keep_evidence"]

save_folder = "/evidence"
os.makedirs(save_folder, exist_ok=True)

class EventProcessor:
    def __init__(self, max_concurrent_tasks=3):
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.task_status = {}

    def beautify(self, event_id):
        status = self.task_status[event_id].copy()
        status['start_time'] = convert_timestamp_to_datetime(status['start_time']) if 'start_time' in status else None
        status['end_time'] = convert_timestamp_to_datetime(status['end_time']) if 'end_time' in status else None
        status['event_time'] = convert_timestamp_to_datetime(status['event_time']) if 'event_time' in status else None
        status['processing_time'] = round(status['processing_time'], 2) if 'processing_time' in status else None
        return status

event_processor = EventProcessor(max_concurrent_tasks=3)

@app.agent(consume_topic)
async def consumer(messages):
    async for message in messages:
        event = None
        try:
            try:
                event = BaseEvent.from_dict(message)
                event.event_id = str(uuid4())
            except Exception as e:
                logger.error(f"Error when parsing message: {e} --- {message['name']} --- {message['camera_id']}")
                continue

            event_processor.task_status[event.event_id] = {
                'status': 'received',
                'start_time': time.time(),
                'event_time': event.detections[-1]["extra_information"]["end_time"],
                'event_name': event.name,
                'camera_id': event.camera_id,
            }
            task = asyncio.create_task(process_event_with_semaphore(event))
            await asyncio.wait_for(task, timeout=90)  # Timeout after 90 seconds


        except Exception as e:
            logger.error(f"Error when processing message: {e}")
            if event and event.event_id in event_processor.task_status:
                del event_processor.task_status[event.event_id]


async def process_event_with_semaphore(event):
    """Process event with semaphore to limit the number of concurrent tasks"""
    try:
        async with event_processor.semaphore:
            logger.info(f"Starting process for event {event.event_id} - {event.name} - {event.camera_id}")
            event_processor.task_status[event.event_id].update({'status': 'processing'})

            if event_processor.task_status[event.event_id]['event_time'] < time.time() - 3600 * 8:
                logger.warning(f"Event {event.event_id} is too old (more than 8 hours) -> Skip processing")
                event_processor.task_status[event.event_id].update({'status': 'failed'})
                return

            # Process event
            result = await process_event_message(event)

            # Update status
            event_processor.task_status[event.event_id].update({
                'status': 'completed',
                'end_time': time.time(),
                'processing_time': time.time() - event_processor.task_status[event.event_id]['start_time']
            })

            return result

    except Exception as e:
        logger.error(f"Error processing event {event.event_id} - {event.name} - {event.camera_id}: {e}")
        event_processor.task_status[event.event_id].update({
            'status': 'failed',
            'error': str(e),
            'end_time': time.time()
        })
        if cfg.deploy_env not in ["PRODUCTION", "STAGING"]:
            raise  # re-raise the exception to show the error in the logs

    finally:
        if event_processor.task_status[event.event_id]["status"] == "completed":
            logger.info(f"Finish event {event_processor.beautify(event.event_id)}")
        elif event_processor.task_status[event.event_id]["status"] == "failed":
            logger.error(f"Failed event {event_processor.beautify(event.event_id)}")
        else:
            logger.warning(f"Event {event_processor.beautify(event.event_id)} is not completed")

        # Cleanup task
        if event.event_id in event_processor.task_status:
            del event_processor.task_status[event.event_id]


async def process_event_message(event):
    start_time = time.time()
    event_id = event.event_id

    logger.info(f"Memory before processing: {psutil.virtual_memory().used / (1024 ** 3):.2f} GB")
    logger.info(f"==================== Start processing event {event_id} ====================")
    try:
        input_video_urls = []
        input_extra_informations = []
        event_box = []
        event_detections_dict = {}
        for det in event.detections:
            input_video_urls.append(det["video_url"])
            input_extra_informations.append(det["extra_information"])
            event_box.append(det["bbox"])

            if det["video_url"] not in event_detections_dict:
                event_detections_dict[det["video_url"]] = [det]
            else:
                event_detections_dict[det["video_url"]].append(det)

        input_video_urls = sorted(set(input_video_urls))
        event_union_box = get_union_box(event_box)

        # Check if the event is recheck event
        is_recheck = False
        if event.name in cfg.recheck_with_llava.split(","):
            is_recheck = True

            # Only get the last 2 videos for recheck
            input_video_urls = input_video_urls[-2:]

            if event.name in cfg.event_extend_bbox:
                event_union_box = extend_bbox(event_union_box, margin_ratio=cfg.event_extend_bbox[event.name])
            else:
                event_union_box = extend_bbox(event_union_box, margin_ratio=0.3)

        logger.info("Recheck event: {}".format(is_recheck))

        # Init save paths
        thumbnail_path, video_path, img_path, crop_video_path, minio_thumbnail_path, \
        minio_video_path, minio_img_path, evidence_base_dir = init_save_paths(
            base_folder=save_folder,
            cam_key=event.camera_id,
            event_name=event.name,
            detect_time=input_extra_informations[-1]["end_time"],
            tenant_id=event.tenant_id,
            area_name=event.area_name,
            event_id=event_id
        )
        save_raw_videos_dir = os.path.join("raw_video", evidence_base_dir)
        os.makedirs(save_raw_videos_dir, exist_ok=True)

        evidence_fps = cfg.fps_for_event[event.name]

        is_real_time = False
        if evidence_fps == -1: #get real time for this event
            is_real_time = True
            input_video_urls = input_video_urls[-2:]
            cap = cv2.VideoCapture(input_video_urls[-1])
            number_frame_of_event_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            raw_fps = int(cap.get(cv2.CAP_PROP_FPS))
            evidence_fps = raw_fps
            if cap.isOpened():
                cap.release()

        # Init video writer
        writer = imageio.get_writer(video_path,
                                    fps=evidence_fps,
                                    codec="libx264",
                                    output_params=[
                                        '-preset', 'medium',
                                        '-crf', '23'
                                    ])
        crop_writer = None
        if is_recheck:
            crop_writer = imageio.get_writer(crop_video_path,
                                             fps=25,
                                             codec="libx264",
                                             output_params=[
                                                 '-preset', 'medium',
                                                 '-crf', '23'
                                             ])

        # Extract event start time and end time
        maximum_length_video = cfg.max_time_for_event[event.name] * evidence_fps  # 20 seconds * 60 fps = 1200 frame
        if len(input_video_urls) > 1:
            max_frame_per_video = maximum_length_video // len(input_video_urls)
        else:
            max_frame_per_video = maximum_length_video  # config time for event * 60 fps = number of frame

        num_frame_llava_recheck = 4 * 25  # 3 seconds * 60 fps = 180 frame

        logger.info(f"Number of video urls: {len(input_video_urls)}")
        # main loop to extract video
        event_frame_id = event.frame_id
        fill_missing_bbox_count = 30
        for video_idx, input_video_url in enumerate(input_video_urls):
            video_name = os.path.basename(input_video_url)

            # Copy video to evidence folder
            # shutil.copy2(input_video_url, save_raw_videos_dir)
            target_path = os.path.join(save_raw_videos_dir, video_name)
            shutil.copyfile(input_video_url, target_path)

            # save AI output to json file
            with open(os.path.join(save_raw_videos_dir, video_name.replace(".mp4", ".json")), "w+") as jf:
                jf.write(json.dumps(event_detections_dict[input_video_url], indent=4))

            cap = cv2.VideoCapture(input_video_url)
            number_frame_of_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            event_detections = event_detections_dict[input_video_url]

            event_detections_frame_key = {}
            for det in event_detections:
                if det["frame_id"] in event_detections_frame_key:
                    event_detections_frame_key[det["frame_id"]].append(det)
                else:
                    event_detections_frame_key[det["frame_id"]] = [det]

            start_frame_id = min(event_detections_frame_key)
            end_frame_id = max(event_detections_frame_key)
            event_frame_id = end_frame_id

            if len(input_video_urls) == 1:
                start_frame_id = max(0, start_frame_id - 60) # start before 60 frames
                end_frame_id = min(number_frame_of_video - 1, end_frame_id + 60) # end after 60 frames
                if is_real_time:
                    start_frame_id = max(0, event_frame_id - int(maximum_length_video * 0.7)) #get 70% time before event
                    end_frame_id = min(number_frame_of_video - 1, event_frame_id + int(maximum_length_video * 0.3)) #get 30% time after event
                    max_frame_per_video = end_frame_id - start_frame_id + 1
            elif video_idx == 0:
                start_frame_id = max(0, start_frame_id - 60)
                end_frame_id = number_frame_of_video - 1
                if is_real_time:
                    det_in_last_video = event_detections_dict[input_video_urls[-1]]
                    event_frame_id_last_video = max(int(d['frame_id']) for d in det_in_last_video)
                    frame_before_event = int(maximum_length_video * 0.7) - event_frame_id_last_video
                    if frame_before_event <= 0:
                        continue
                    start_frame_id = max(0, end_frame_id - frame_before_event)
                    max_frame_per_video = end_frame_id - start_frame_id + 1
            elif video_idx == len(input_video_urls) - 1:
                max_frame_per_video = maximum_length_video - ((len(input_video_urls) - 1) * max_frame_per_video)
                start_frame_id = 0
                end_frame_id = min(number_frame_of_video - 1, end_frame_id + 60)
                if is_real_time:
                    start_frame_id = max(0, event_frame_id - int(maximum_length_video * 0.7)) #get 70% time before event
                    end_frame_id = min(number_frame_of_video - 1, event_frame_id + int(maximum_length_video * 0.3)) #get 30% time after event
                    max_frame_per_video = end_frame_id - start_frame_id + 1

            list_frame_ids = list(np.linspace(start_frame_id, end_frame_id, max_frame_per_video, dtype=int))
            logger.info(f"Video IDX: {video_idx} - Len of list frame id: {len(list_frame_ids)}")

            if event.name.upper() in ['PL02', 'VEH03']:
                fill_missing_bbox_count = number_frame_of_video

            current_dets_keeper = []
            time_keeper = fill_missing_bbox_count

            frame_id = start_frame_id - 1
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)

            while cap.isOpened():
                frame_id += 1
                if frame_id > end_frame_id:
                    break

                ret = cap.grab()
                if not ret:
                    break

                # if frame_id < start_frame_id:
                #     continue

                # Draw frame with bbox
                current_dets = event_detections_frame_key.get(frame_id, [])

                # Keep the last detection for 30 frames (0.5s)
                if len(current_dets) == 0:
                    if time_keeper > 0:
                        current_dets = current_dets_keeper
                        time_keeper -= 1
                else:
                    current_dets_keeper = current_dets
                    # Reset time_keeper
                    time_keeper = fill_missing_bbox_count

                if (
                    is_recheck
                    and (event_frame_id - num_frame_llava_recheck) < frame_id <= event_frame_id
                ):
                    # Crop frame around event box
                    status, frame = cap.retrieve()
                    cropped_frame = frame[event_union_box[1]:event_union_box[3],
                                    event_union_box[0]:event_union_box[2]].copy()

                    cropped_frame = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
                    crop_writer.append_data(cropped_frame)

                    # crop_writer.write(cropped_frame)
                    # cv2.waitKey(1)

                # drop frame
                if frame_id not in list_frame_ids:
                    continue

                status, frame = cap.retrieve()
                for det in current_dets:
                    frame = draw_bb(frame, det["bbox"], (0, 0, 255), label=cfg.event_type_names.get(event.name, event.name))

                ## save thumbnail image for the event
                if len(current_dets) and not os.path.exists(img_path) and frame_id >0:
                    thumbnail = cv2.resize(frame, (360, 240))
                    _, buffer = cv2.imencode('.jpg', thumbnail)
                    # Get the size of the encoded image in bytes
                    image_size_bytes = len(buffer)

                    # Convert bytes to kilobytes
                    image_size_kb = image_size_bytes / 1024
                    if image_size_kb > 30:
                        cv2.imwrite(thumbnail_path, thumbnail)
                        cv2.imwrite(img_path, frame)
                        logger.info(f"Save thumbnail and image for event {event.name} at {thumbnail_path} and {img_path}")

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                writer.append_data(rgb_frame)

                if event.name.upper() in ['PL02', 'VEH03']:
                    next_index_frame = list_frame_ids.index(frame_id) + 1
                    if next_index_frame > len(list_frame_ids) - 1:
                        break
                    frame_id = list_frame_ids[next_index_frame] - 1
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
            else:
                cap.release()
                logger.info(f"Finish processing video {input_video_url}")

            logger.info(f"Memory during processing: {psutil.virtual_memory().used / (1024 ** 3):.2f} GB")

        if is_recheck:
            crop_writer.close()
        writer.close()

        logger.info(f"Video processing took {time.time() - start_time:.2f} seconds")

        logger.info(f"Waiting for video to be stored in evidence folder")
        if is_recheck:
            wait_store_check = await check_exist_and_wait_for_files([crop_video_path, video_path, thumbnail_path, img_path], timeout=20)
        else:
            wait_store_check = await check_exist_and_wait_for_files([video_path, thumbnail_path, img_path], timeout=20)

        if not wait_store_check:
            logger.info(f"Time taken for event {event.name}: {time.time() - start_time:.2f} seconds")
            logger.warning(f"Event {event.name}: Video for event is not found -> Skip sending event to kafka")
            return


        if is_recheck:

            # Verify event by llava video
            logger.info(">>>> LLAVA START: {} - URL: {}".format(event.name, crop_video_path))
            is_valid_event = await verify_event_by_llava(video_path=crop_video_path, event_type=event.name)
            logger.info("<<<<<LLAVA END: Result: {}".format(is_valid_event))

            llava_evidence_base_dir = evidence_base_dir + f"_llava_{is_valid_event}"

            video_path = video_path.replace(evidence_base_dir, llava_evidence_base_dir)
            thumbnail_path = thumbnail_path.replace(evidence_base_dir, llava_evidence_base_dir)
            img_path = img_path.replace(evidence_base_dir, llava_evidence_base_dir)
            crop_video_path = crop_video_path.replace(evidence_base_dir, llava_evidence_base_dir)

            os.rename(evidence_base_dir, llava_evidence_base_dir)
            evidence_base_dir = llava_evidence_base_dir

            logger.info(f"Waiting for evidence folder to be renamed")
            wait_store_check = await check_exist_and_wait_for_files([video_path, thumbnail_path, img_path], timeout=10)
            if not wait_store_check:
                logger.info(f"Time taken for event {event.name}: {time.time() - start_time:.2f} seconds")
                logger.warning(f"Event {event.name}: Video for event is not found -> Skip sending event to kafka")
                return

            if not is_valid_event:
                if REMOVE_EVIDENCE:
                    # Remove all files in evidence folder but keep llava evidence for checking
                    delete_folder_with_exclusions(evidence_base_dir,
                                                  exclusions=[video_path, img_path, crop_video_path])
                logger.info(f"Time taken for event {event.name}: {time.time() - start_time:.2f} seconds")
                logger.warning(f"Event {event.name}: {event_id} is fail when checking llava -> Skip sending event to kafka")
                return

        # Push evidence video to minio storage
        start_upload = time.time()
        video_url = minio_client.upload_file(cfg.storage_bucket, minio_video_path, video_path)
        thumbnail_url = minio_client.upload_file(cfg.storage_bucket, minio_thumbnail_path, thumbnail_path)
        img_url = minio_client.upload_file(cfg.storage_bucket, minio_img_path, img_path)
        logger.info(f"Upload to MinIO took {time.time() - start_upload:.2f} seconds")

        if not all([video_url, thumbnail_url, img_url]):
            logger.error(f"Failed to upload video to Minio")

            event_time = input_extra_informations[-1]["start_time"] + int(event_frame_id) // 25
            data = {
                "camera_id": event.camera_id,
                "event_type": event.name,
                "event_id": event_id,
                "status": "OPEN",
                "image_url": img_url,
                "video_url": video_url,
                "thumbnail_url": thumbnail_url,
                "event_time": convert_timestamp_to_datetime(event_time),
                "push_time": event_time,
                "tenant_id": event.tenant_id,
                "area_name": event.area_name,
            }

            with open(os.path.join(save_raw_videos_dir, event_id + "-upload_failed_event.json"), "w+") as jf:
                jf.write(json.dumps(data, indent=4))

            logger.warning(">>>>> [Upload failed] Finish processing event {}, camera id: {}".format(event.name, event.camera_id))
            logger.info(f"Time taken for event {event.name}: {time.time() - start_time:.2f} seconds")
            return

        ## Replace if storage_url is internal ip, storage_domain_url is domain url
        if cfg.storage_domain_url and cfg.storage_url != cfg.storage_domain_url:
            img_url = img_url.replace("http://", "").replace("https://", "")
            video_url = video_url.replace("http://", "").replace("https://", "")
            thumbnail_url = thumbnail_url.replace("http://", "").replace("https://", "")

            img_url = img_url.replace(cfg.storage_url, cfg.storage_domain_url)
            video_url = video_url.replace(cfg.storage_url, cfg.storage_domain_url)
            thumbnail_url = thumbnail_url.replace(cfg.storage_url, cfg.storage_domain_url)


        event_time = input_extra_informations[-1]["start_time"] + int(event_frame_id) // 25
        data = {
            "camera_id": event.camera_id,
            "event_type": event.name,
            "event_id": event_id,
            "status": "OPEN",
            "image_url": img_url,
            "video_url": video_url,
            "thumbnail_url": thumbnail_url,
            "event_time": convert_timestamp_to_datetime(event_time),
            "push_time": event_time,
            "tenant_id": event.tenant_id,
            "area_name": event.area_name,
        }
        logger.info(f"Send event to kafka {data}")
        kafka_producer.send(
            cfg.kafka_event_topic, value=json.dumps(data).encode("utf-8")
        )
        kafka_producer.flush()

        if cfg.eme_events_collector_url:
            post_to_event_collector(cfg.eme_events_collector_url, event.name)

        # Remove all files in evidence folder
        if REMOVE_EVIDENCE:
            delete_folder_with_exclusions(evidence_base_dir)

    except Exception as e:
        logger.error(f"Error processing event {event_id}: {e}")
    finally:
        # Clean up large objects explicitly
        if 'writer' in locals() and writer:
            writer.close()
        if 'crop_writer' in locals() and crop_writer:
            crop_writer.close()
        if 'cap' in locals() and cap:
            cap.release()

        # delete all variables
        del event_detections_dict
        del event_detections

        # Force garbage collection
        gc.collect()
        logger.info(f"Time taken for event {event.name}: {time.time() - start_time:.2f} seconds")
        logger.info(f"Memory after processing: {psutil.virtual_memory().used / (1024 ** 3):.2f} GB")
        logger.info(f"==================== Finish processing event {event_id} ====================")
