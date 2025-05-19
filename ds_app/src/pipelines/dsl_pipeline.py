import sys

sys.path.append("../")

from dsl.dsl import *
import os
import pyds
import time
from datetime import datetime
import json
import logging
from utils.FPS import GETFPS

from kafka import KafkaProducer
from kafka.errors import KafkaTimeoutError

frame_interval = int(os.getenv("FRAME_PROCESS_INTERVAL", default=1))
is_file_sink = int(os.getenv("FILE_SINK", default=0))

has_error = False
input_srcs_bk = []
cams_bk = []
g_pipeline_name = 'pipeline'

class Component:
    def __init__(self, id: int) -> None:
        self.source_name = f"uri-source-{id}"

def eos_event_listener(client_data):
    global g_pipeline_name
    logging.info("Pipeline EOS event")
    dsl_pipeline_stop(g_pipeline_name)
    dsl_main_loop_quit()

def state_change_listener(old_state, new_state, client_data):
    global g_pipeline_name
    print("previous state = ", old_state, ", new state = ", new_state)
    if new_state == DSL_STATE_PLAYING:
        dsl_pipeline_dump_to_dot(g_pipeline_name, "state-playing")

class DSL_Pipeline:
    def __init__(
        self,
        input_srcs: list,
        cam_ids: list,
        pgie_infer_config_file: str,
        tracker_config_file: str,
        pipeline_name: str = 'pipeline'
    ) -> None:
        """Create a Deepstream Pipeline.

        Args:
            input_srcs (list): The list sources video URI input (ex: /videos/video1.mp4).
            cam_ids (list): list cam id
            pgie_infer_config_file (str): The configuration file path of the primary inference engine.
            tracker_config_file (str): The configuration file path of the tracker.
        """
        global cams_bk, input_srcs_bk, g_pipeline_name
        logging.info(f"__init__ Pipeline: {pipeline_name}")
        g_pipeline_name = pipeline_name
        cams_bk = cam_ids
        input_srcs_bk = input_srcs
        self.pgie_infer_config_file = pgie_infer_config_file
        self.tracker_config_file = tracker_config_file

        self.init_kafka()

        self.fps_streams = {}

    def init_kafka(self):
        try:
            logging.info(f"Init kafka")
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=[os.getenv("KAFKA_BROKER")],
                request_timeout_ms=5000,
                max_block_ms=5000,
            )
        except Exception as e:
            logging.error(e)
            exit()

    def custom_pad_probe_handler(self, buffer, user_data):
        global has_error, input_srcs_bk, cams_bk
        # Retrieve batch metadata from the gst_buffer
        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(buffer)
        l_frame = batch_meta.frame_meta_list
        while l_frame is not None:
            try:
                frame_meta = pyds.glist_get_nvds_frame_meta(l_frame.data)
                src_index = frame_meta.pad_index
            except StopIteration:
                break

            frame_number = frame_meta.frame_num
            if frame_number == 1:
                logging.info("Running ...")

            if frame_number % frame_interval == 0:
                # print(f"src_index={src_index} Frame Number={frame_number}")
                l_obj = frame_meta.obj_meta_list

                detections = []

                while l_obj is not None:
                    try:
                        # Casting l_obj.data to pyds.NvDsObjectMeta
                        obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
                        track_id = obj_meta.object_id
                        class_id = obj_meta.class_id
                        obj_confidence = obj_meta.confidence
                        obj_label = obj_meta.obj_label
                        rect_params = obj_meta.rect_params
                        x1 = int(rect_params.left)
                        y1 = int(rect_params.top)
                        x2 = int(x1 + rect_params.width)
                        y2 = int(y1 + rect_params.height)

                        detection = {
                            "xyxy": [x1, y1, x2, y2],
                            "confidence": obj_confidence,
                            "track_id": track_id,
                            "class_id": class_id,
                            "class_name": obj_label,
                            "detect_time": time.time(),
                            "video_url": input_srcs_bk[src_index],
                            "cam_id": cams_bk[src_index],
                            "frame_id": frame_number,
                            "push_time": datetime.now().strftime(
                                "%d/%m/%y %H:%M:%S"
                            ),
                        }
                        detections.append(detection)

                    except StopIteration:
                        break

                    except Exception as e:
                        logging.error(f"++++ list src {src_index}   --> bk: {input_srcs_bk}")
                        logging.error(f"++++ list cam   ----> bk: {cams_bk}")
                        logging.error(e)
                        has_error = True
                        break

                    try:
                        l_obj = l_obj.next
                    except StopIteration:
                        break

                try:
                    message = {
                        "cam_id": cams_bk[src_index],
                        "frame_id": frame_number,
                        "detections": detections,
                        "video_url": input_srcs_bk[src_index],
                        "push_time": datetime.now().strftime(
                            "%d/%m/%y %H:%M:%S"
                        ),
                    }

                    # logging.info(message)

                    try:
                        self.kafka_producer.send(
                            os.getenv("KAFKA_DEEPSTREAM_TOPIC"),
                            json.dumps(message).encode("utf-8"),
                        )
                    except KafkaTimeoutError as e:
                        self.init_kafka()

                except Exception as e:
                    logging.error(f"---- {src_index}")
                    logging.error(e)
                    has_error = True

            # FPS
            self.fps_streams["stream{0}".format(src_index)].update_fps()
            if frame_number % 25 == 0:
                fps = self.fps_streams["stream{0}".format(src_index)].get_fps()
                logging.info(f"fps stream {src_index}  :  {fps}")

            try:
                l_frame = l_frame.next
            except StopIteration:
                break
        return DSL_PAD_PROBE_OK
    
    # def eos_event_listener(self, client_data):
    #     logging.info("Pipeline EOS event")
    #     dsl_pipeline_stop(self.pipeline_name)
    #     dsl_main_loop_quit()

    # ##
    # # Function to be called on every change of Pipeline state
    # ##
    # def state_change_listener(self, old_state, new_state, client_data):
    #     print("previous state = ", old_state, ", new state = ", new_state)
    #     if new_state == DSL_STATE_PLAYING:
    #         dsl_pipeline_dump_to_dot(self.pipeline_name, "state-playing")

    def run(self) -> bool:
        global has_error,input_srcs_bk,g_pipeline_name
        # Since we're not using args, we can Let DSL initialize GST on first call
        while True:
            src_elements = []

            if len(input_srcs_bk) == 0:
                logging.error(f"Source empty: {input_srcs_bk}")
                break
            
            for idx, src in enumerate(input_srcs_bk):
                component = Component(idx)
                # New URI File Source using the filespec defined above
                logging.info(f"{component.source_name}------------- {src}")
                retval = dsl_source_uri_new(
                    component.source_name, src, False, False, 0
                )
                if retval != DSL_RETURN_SUCCESS:
                    break
                src_elements.append(component.source_name)    
                self.fps_streams["stream{0}".format(idx)]=GETFPS(idx)

            # New Primary GIE using the filespecs above with interval = 0
            retval = dsl_infer_gie_primary_new(
                "primary-gie", self.pgie_infer_config_file, None, 0
            )
            if retval != DSL_RETURN_SUCCESS:
                break

            # New IOU Tracker, setting operational width and hieght
            retval = dsl_tracker_new(
                "tracker", self.tracker_config_file, 480, 272
            )
            if retval != DSL_RETURN_SUCCESS:
                break

            # New Custom Pad Probe Handler to call Nvidia's example callback
            # for handling the Batched Meta Data
            retval = dsl_pph_custom_new(
                "custom-pph",
                client_handler=self.custom_pad_probe_handler,
                client_data=None,
            )

            # New OSD with text, clock and bbox display all enabled.
            retval = dsl_osd_new(
                "on-screen-display",
                text_enabled=True,
                clock_enabled=True,
                bbox_enabled=True,
                mask_enabled=False,
            )
            if retval != DSL_RETURN_SUCCESS:
                break

            # Add the custom PPH to the Sink pad of the OSD
            retval = dsl_osd_pph_add(
                "on-screen-display", handler="custom-pph", pad=DSL_PAD_SINK
            )
            if retval != DSL_RETURN_SUCCESS:
                break

            # New Sink
            if is_file_sink:
                now_time = datetime.now().strftime("%d_%m_%yT%H_%M_%S")
                file_name = f"/app/{component.source_name}_{now_time}.mkv"
                retval = dsl_sink_file_new(
                    "final-sink",
                    file_name,
                    DSL_CODEC_H264,
                    DSL_CONTAINER_MKV,
                    0,
                    0,
                )
            else:
                retval = dsl_sink_fake_new("final-sink")
            if retval != DSL_RETURN_SUCCESS:
                break

            # Add all the components to our pipeline
            src_elements.extend(
                [
                    "primary-gie",
                    "tracker",
                    "on-screen-display",
                    "final-sink",
                    None,
                ]
            )
            retval = dsl_pipeline_new_component_add_many(
                g_pipeline_name, src_elements
            )
            if retval != DSL_RETURN_SUCCESS:
                break

            ## Add the listener callback functions defined above
            logging.info("Set state change listener")
            retval = dsl_pipeline_state_change_listener_add(
                g_pipeline_name, state_change_listener, None
            )
            if retval != DSL_RETURN_SUCCESS:
                break

            logging.info("Set EOS listener")
            retval = dsl_pipeline_eos_listener_add(
                g_pipeline_name, eos_event_listener, None
            )
            if retval != DSL_RETURN_SUCCESS:
                break

            # Play the pipeline
            logging.info("Play pipeline")
            retval = dsl_pipeline_play(g_pipeline_name)
            if retval != DSL_RETURN_SUCCESS:
                break

            dsl_main_loop_run()
            retval = DSL_RETURN_SUCCESS
            break

        # Print out the final result
        logging.info(dsl_return_value_to_string(retval))

        try:
            dsl_pipeline_delete_all()
            dsl_component_delete_all()
        except Exception as e:
            logging.error(f"Pipeline EOS Exception: {e}")
        logging.info (f"has_error : {has_error}")
        time.sleep(5)
        return has_error