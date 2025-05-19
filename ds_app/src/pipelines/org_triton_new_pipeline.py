import os
import sys
import time
from datetime import datetime, timezone

from loguru import logger

import pyds
from kafka import KafkaProducer
from kafka.errors import KafkaTimeoutError
from src.models.input_data import InputData

sys.path.append("../")

from dsl.dsl import *

import json

import gi

gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst
import math
from utils.bus_call import bus_call
from utils.FPS import PERF_DATA

MAX_DISPLAY_LEN = 64
MUXER_BATCH_TIMEOUT_USEC = 40000
TILED_OUTPUT_WIDTH = 1920
TILED_OUTPUT_HEIGHT = 1080
OSD_PROCESS_MODE = 0
OSD_DISPLAY_TEXT = 1
fps_log_interval = 10000

cam_sources = []
cam_ids = []
extra_informations = []

frame_interval = int(os.getenv("FRAME_PROCESS_INTERVAL", default=1))
is_file_sink = int(os.getenv("FILE_SINK", default=0))

has_error = False
g_pipeline_name = 'pipeline'

try:
    kafka_producer = KafkaProducer(
        bootstrap_servers=[os.getenv("KAFKA_BROKER")],
        request_timeout_ms=5000,
        max_block_ms=5000,
    )
except Exception as e:
    logger.error(f"Init Kafka error: {str(e)}")
    exit()


class Component:
    def __init__(self, id: int) -> None:
        self.source_name = f"uri-source-{id}"


def eos_event_listener(client_data):
    global g_pipeline_name
    logger.info("Pipeline EOS event")
    dsl_pipeline_stop(g_pipeline_name)
    dsl_main_loop_quit()


def state_change_listener(old_state, new_state, client_data):
    global g_pipeline_name
    print("previous state = ", old_state, ", new state = ", new_state)
    if new_state == DSL_STATE_PLAYING:
        dsl_pipeline_dump_to_dot(g_pipeline_name, "state-playing")


def cb_newpad(decodebin, decoder_src_pad, data):
    caps = decoder_src_pad.get_current_caps()
    if not caps:
        caps = decoder_src_pad.query_caps()
    gststruct = caps.get_structure(0)
    gstname = gststruct.get_name()
    source_bin = data
    features = caps.get_features(0)

    # Need to check if the pad created by the decodebin is for video and not
    # audio.
    if (gstname.find("video") != -1):
        # Link the decodebin pad only if decodebin has picked nvidia
        # decoder plugin nvdec_*. We do this by checking if the pad caps contain
        # NVMM memory features.
        if features.contains("memory:NVMM"):
            # Get the source bin ghost pad
            bin_ghost_pad = source_bin.get_static_pad("src")
            if not bin_ghost_pad.set_target(decoder_src_pad):
                sys.stderr.write("Failed to link decoder src pad to source bin ghost pad\n")
        else:
            sys.stderr.write(" Error: Decodebin did not pick nvidia decoder plugin.\n")


def decodebin_child_added(child_proxy, Object, name, user_data):
    if (name.find("decodebin") != -1):
        Object.connect("child-added", decodebin_child_added, user_data)

    if "source" in name:
        source_element = child_proxy.get_by_name("source")
        if source_element.find_property('drop-on-latency') != None:
            Object.set_property("drop-on-latency", True)


class DSL_Pipeline:
    def __init__(
            self,
            input_srcs: list,
            cam_ids: list,
            number_branches=2,
            pgie_config_file_paths=[],
            sgie_config_file_paths=[],
            sgie_rule_names=[],
            model_topic_mappings=[],
            model_id_mapping = [],
            camera_topics_mapping={},
            kafka_topics = [],
            target_class_names_dict={},
            pipeline_name: str = 'pipeline',
            disable_probe=False
    ) -> None:

        global g_pipeline_name
        logger.info(f"__init__ Pipeline: {pipeline_name}")
        g_pipeline_name = pipeline_name
        self.input_srcs_bk = input_srcs
        self.is_live = False
        self.disable_probe = disable_probe
        self.number_branches = number_branches
        self.cam_ids = cam_ids
        self.pgie_config_file_paths = pgie_config_file_paths
        self.sgie_config_file_paths = sgie_config_file_paths
        self.init_pipeline(len(input_srcs), number_branches)
        self.set_property(len(input_srcs), number_branches)
        self.sgie_rule_names = sgie_rule_names
        self.model_topic_mappings = model_topic_mappings
        self.camera_topics_mapping = camera_topics_mapping
        self.target_class_names_dict = target_class_names_dict
        self.model_id_mapping = model_id_mapping
        self.kafka_topics = kafka_topics

        self.link_elements()

        self.init_metrics(len(input_srcs), number_branches)

    def init_metrics(self, number_sources, number_branches):
        for idx in range(number_branches):
            setattr(self, f"perf_data_{idx}", PERF_DATA(self.model_topic_mappings[idx], number_sources))

    def init_pipeline(self, number_sources, number_branches=2):
        # Standard GStreamer initialization
        Gst.init(None)

        # Create Pipeline
        self.pipeline = Gst.Pipeline()
        if not self.pipeline:
            sys.stderr.write("Unable to create Pipeline \n")

        # Create nvstreammux
        self.streammux = Gst.ElementFactory.make("nvstreammux", "streammux")
        if not self.streammux:
            sys.stderr.write("Unable to create NvStreamMux \n")

        self.pipeline.add(self.streammux)

        # Create sources
        for i in range(number_sources):
            uri_name = self.input_srcs_bk[i]
            if uri_name.find("rtsp://") == 0:
                self.is_live = True
            source_bin = self.create_source_bin(i, uri_name)
            if not source_bin:
                sys.stderr.write("Unable to create source bin \n")
            self.pipeline.add(source_bin)

            padname = "sink_%u" % i
            sinkpad = self.streammux.request_pad_simple(padname)
            if not sinkpad:
                sys.stderr.write("Unable to create sink pad bin \n")
            srcpad = source_bin.get_static_pad("src")
            if not srcpad:
                sys.stderr.write("Unable to create src pad bin \n")
            srcpad.link(sinkpad)

        self.tee = Gst.ElementFactory.make("tee", "tee")

        if not self.tee:
            raise RuntimeError("Unable to create tee")
        self.pipeline.add(self.tee)

        for idx in range(number_branches):
            queue = Gst.ElementFactory.make("queue", f"queue_{idx}")
            if not queue:
                raise RuntimeError("Unable to create queue")
            setattr(self, f"queue_{idx}", queue)
            self.pipeline.add(queue)

        for idx in range(number_branches):
            pgie = Gst.ElementFactory.make("nvinferserver", f"primary-inference-{idx}")
            if not pgie:
                raise RuntimeError("Unable to create pgie")
            setattr(self, f"pgie_{idx}", pgie)
            self.pipeline.add(pgie)

        for idx in range(number_branches):
            sgie_config_file_path = self.sgie_config_file_paths[idx]
            if sgie_config_file_path is not None:
                sgie = Gst.ElementFactory.make("nvinferserver", f"secondary-inference-{idx}")
                if not sgie:
                    raise RuntimeError("Unable to create sgie")
                setattr(self, f"sgie_{idx}", sgie)
                self.pipeline.add(sgie)

        if self.disable_probe:
            for idx in range(number_branches):
                nvdslogger = Gst.ElementFactory.make("nvdslogger", f"nvdslogger-{idx}")
                if not nvdslogger:
                    raise RuntimeError("Unable to create nvdslogger")
                setattr(self, f"nvdslogger_{idx}", nvdslogger)
                self.pipeline.add(nvdslogger)

        for idx in range(number_branches):
            tiler = Gst.ElementFactory.make("nvmultistreamtiler", f"nvtiler-{idx}")
            if not tiler:
                raise RuntimeError("Unable to create tiler")
            setattr(self, f"tiler_{idx}", tiler)
            self.pipeline.add(tiler)

        for idx in range(number_branches):
            nvvidconv = Gst.ElementFactory.make("nvvideoconvert", f"convertor-{idx}")
            if not nvvidconv:
                raise RuntimeError("Unable to create videoconvert")
            setattr(self, f"nvvidconv_{idx}", nvvidconv)
            self.pipeline.add(nvvidconv)

        for idx in range(number_branches):
            nvosd = Gst.ElementFactory.make("nvdsosd", f"onscreendisplay-{idx}")
            if not nvosd:
                raise RuntimeError("Unable to create on screen display")
            setattr(self, f"nvosd_{idx}", nvosd)
            self.pipeline.add(nvosd)

        for idx in range(number_branches):
            sink = Gst.ElementFactory.make("fakesink", f"fakesink-{idx}")
            if not sink:
                raise RuntimeError("Unable to create sink")
            setattr(self, f"sink_{idx}", sink)
            self.pipeline.add(sink)

    def set_property(self, number_sources, number_branches=2):
        # OSD
        for idx in range(number_branches):
            nvosd = getattr(self, f"nvosd_{idx}")
            nvosd.set_property('process-mode', OSD_PROCESS_MODE)
            nvosd.set_property('display-text', OSD_DISPLAY_TEXT)

        # for idx in range(number_branches):
        #     queue = getattr(self, f"queue_{idx}")
        #     queue.set_property('leaky', 1)
        # Sink
        for idx in range(number_branches):
            sink = getattr(self, f"sink_{idx}")
            sink.set_property('enable-last-sample', 0)
            sink.set_property('sync', 0)
            sink.set_property("qos", 0)

        if self.is_live:
            self.streammux.set_property('live-source', 1)

        # Streammux
        self.streammux.set_property('width', 1920)
        self.streammux.set_property('height', 1080)
        self.streammux.set_property('batch-size', number_sources)
        self.streammux.set_property('batched-push-timeout', MUXER_BATCH_TIMEOUT_USEC)
        # self.streammux.set_property('buffer-pool-size', 4)

        # Pgie
        for idx in range(number_branches):
            pgie = getattr(self, f"pgie_{idx}")
            pgie.set_property('config-file-path', self.pgie_config_file_paths[idx])
            pgie.set_property('interval', frame_interval)
            pgie.set_property("batch-size", number_sources)

        # Sgie
        for idx in range(number_branches):
            if hasattr(self, f"sgie_{idx}"):
                sgie = getattr(self, f"sgie_{idx}")
                sgie.set_property('config-file-path', self.sgie_config_file_paths[idx])

        tiler_rows = int(math.sqrt(number_sources))
        tiler_columns = int(math.ceil((1.0 * number_sources) / tiler_rows))

        for idx in range(number_branches):
            tiler = getattr(self, f"tiler_{idx}")
            tiler.set_property("rows", tiler_rows)
            tiler.set_property("columns", tiler_columns)
            tiler.set_property("width", TILED_OUTPUT_WIDTH)
            tiler.set_property("height", TILED_OUTPUT_HEIGHT)

    def link_elements(self):
        self.streammux.link(self.tee)
        for idx in range(self.number_branches):
            sgie = None
            queue = getattr(self, f"queue_{idx}")
            pgie = getattr(self, f"pgie_{idx}")

            if hasattr(self, f"sgie_{idx}"):
                sgie = getattr(self, f"sgie_{idx}")

            if self.disable_probe:
                nvdslogger = getattr(self, f"nvdslogger_{idx}")
            tiler = getattr(self, f"tiler_{idx}")
            nvvidconv = getattr(self, f"nvvidconv_{idx}")
            nvosd = getattr(self, f"nvosd_{idx}")
            sink = getattr(self, f"sink_{idx}")

            queue.link(pgie)

            if sgie is not None:
                pgie.link(sgie)
                # if self.disable_probe:
                #     sgie.link(nvdslogger)
                #     nvdslogger.link(tiler)
                # else:
                #     sgie.link(tiler)
                sgie.link(sink)
            else:
                # if self.disable_probe:
                #     pgie.link(nvdslogger)
                #     nvdslogger.link(tiler)
                # else:
                #     pgie.link(tiler)
                pgie.link(sink)
            # tiler.link(nvvidconv)
            # nvvidconv.link(nvosd)
            # nvosd.link(sink)

            queue_sink_pad = queue.get_static_pad("sink")
            tee_msg_pad = self.tee.get_request_pad('src_%u')
            if not tee_msg_pad:
                raise RuntimeError("Unable to get request pads\n")
            tee_msg_pad.link(queue_sink_pad)

    def run_pipeline(self, inputs: InputData):
        global cam_ids, cam_sources, extra_informations
        cam_sources = inputs.get_src()
        cam_ids = inputs.get_cams_id()
        extra_informations = inputs.get_extra_informations()
        loop = GLib.MainLoop()
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", bus_call, loop)
        for idx in range(self.number_branches):
            if hasattr(self, f"sgie_{idx}"):
                sgie_src_pad = getattr(self, f"sgie_{idx}").get_static_pad("src")

                if not sgie_src_pad:
                    sys.stderr.write(" Unable to get src pad \n")
                else:
                    if not self.disable_probe:
                        custom_user_data = {"branch_idx": idx,
                                            "target_class_names_dict": self.target_class_names_dict,
                                            "model_id" : self.model_id_mapping[idx],
                                            "model_name": self.model_topic_mappings[idx],
                                            "kafka_topic": self.kafka_topics[idx]}
                        rule_name = self.sgie_rule_names[idx]
                        sgie_src_pad.add_probe(Gst.PadProbeType.BUFFER,
                                               getattr(self, f"sgie_src_pad_buffer_probe_{rule_name}"),
                                               custom_user_data)
                        # perf callback function to print fps every 5 sec
                        timeout_id = GLib.timeout_add(fps_log_interval,
                                                      getattr(self, f"perf_data_{idx}").perf_print_callback)
                        setattr(self, f"timeout_id_{idx}", timeout_id)
            else:
                pgie_src_pad = getattr(self, f"pgie_{idx}").get_static_pad("src")

                if not pgie_src_pad:
                    sys.stderr.write(" Unable to get src pad \n")
                else:
                    if not self.disable_probe:
                        custom_user_data = {"branch_idx": idx,
                                            "target_class_names_dict": self.target_class_names_dict,
                                            "model_id": self.model_id_mapping[idx],
                                            "model_name": self.model_topic_mappings[idx],
                                            "kafka_topic": self.kafka_topics[idx]
                                            }
                        pgie_src_pad.add_probe(Gst.PadProbeType.BUFFER, self.pgie_src_pad_buffer_probe,
                                               custom_user_data)
                        # perf callback function to print fps every 5 sec
                        timeout_id = GLib.timeout_add(fps_log_interval,
                                                      getattr(self, f"perf_data_{idx}").perf_print_callback)
                        setattr(self, f"timeout_id_{idx}", timeout_id)

        # start play back and listed to events
        self.pipeline.set_state(Gst.State.PLAYING)
        try:
            loop.run()
        except:
            pass

        # Remove callback
        # if timeout_id1:
        #     GLib.source_remove(timeout_id1)

        # if timeout_id2:
        #     GLib.source_remove(timeout_id2)
        for idx in range(self.number_branches):
            if hasattr(self, f"timeout_id_{idx}"):
                GLib.source_remove(getattr(self, f"timeout_id_{idx}"))

        self.pipeline.set_state(Gst.State.NULL)

    def pgie_src_pad_buffer_probe(self, pad, info, u_data):
        global kafka_producer
        branch_idx = u_data["branch_idx"]
        kafka_topic = u_data["kafka_topic"]
        model_name = u_data["model_name"]
        model_id = u_data["model_id"]
        target_class_names = u_data["target_class_names_dict"].get(model_name, [])
        perf_data = getattr(self, f"perf_data_{branch_idx}")
        gst_buffer = info.get_buffer()
        if not gst_buffer:
            logger.warning("Unable to get GstBuffer")
            return
        # Retrieve batch metadata from the gst_buffer
        # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
        # C address of gst_buffer as input, which is obtained with hash(gst_buffer)

        # Enable latency measurement via probe if environment variable NVDS_ENABLE_LATENCY_MEASUREMENT=1 is set.
        # To enable component level latency measurement, please set environment variable
        # NVDS_ENABLE_COMPONENT_LATENCY_MEASUREMENT=1 in addition to the above.
        # if measure_latency1:
        #     num_sources_in_batch = pyds.nvds_measure_buffer_latency(hash(gst_buffer))
        #     if num_sources_in_batch == 0:
        #         logger.warning("Unable to get number of sources in GstBuffer for latency measurement")

        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
        l_frame = batch_meta.frame_meta_list
        while l_frame is not None:
            try:
                frame_meta = pyds.glist_get_nvds_frame_meta(l_frame.data)
                src_index = frame_meta.pad_index
            except StopIteration:
                break

            frame_number = frame_meta.frame_num

            if frame_number % (frame_interval + 1) == 0:
                l_obj = frame_meta.obj_meta_list

                detections = []

                while l_obj is not None:
                    try:
                        # Casting l_obj.data to pyds.NvDsObjectMeta
                        obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
                        unique_component_id = obj_meta.unique_component_id
                        class_id = obj_meta.class_id
                        obj_confidence = obj_meta.confidence
                        obj_label = obj_meta.obj_label
                        rect_params = obj_meta.rect_params
                        x1 = int(rect_params.left)
                        y1 = int(rect_params.top)
                        x2 = int(x1 + rect_params.width)
                        y2 = int(y1 + rect_params.height)

                        # Skip if object is not in target
                        if len(target_class_names) and not obj_label in target_class_names:
                            try:
                                l_obj = l_obj.next
                                continue
                            except StopIteration:
                                break

                        # Skip if confidence is too small
                        if obj_confidence < 0:
                            try:
                                l_obj = l_obj.next
                                continue
                            except StopIteration:
                                break

                        detection = {
                            "xyxy": [x1, y1, x2, y2],
                            "confidence": obj_confidence,
                            "class_id": class_id,
                            "class_name": obj_label,
                            "detect_time": datetime.now(timezone.utc).timestamp(),
                            "video_url": cam_sources[src_index],
                            "cam_id": cam_ids[src_index],
                            "frame_id": frame_number,
                            "push_time": datetime.now(timezone.utc).timestamp()
                        }
                        if model_id ==  unique_component_id:
                            detections.append(detection)

                    except StopIteration:
                        break

                    except Exception as e:
                        logger.error(f"Error when process frame: {str(e)}")
                        break

                    try:
                        l_obj = l_obj.next
                    except StopIteration:
                        break

                try:
                    message = {
                        "cam_id": cam_ids[src_index],
                        "frame_id": frame_number,
                        "detections": detections,
                        "video_url": cam_sources[src_index],
                        "push_time": datetime.now(timezone.utc).timestamp(),
                        "extra_information": extra_informations[src_index]
                    }

                    try:
                        allow_kafka_topics = self.camera_topics_mapping.get(self.cam_ids[src_index])
                        if allow_kafka_topics :
                            if model_name in allow_kafka_topics:
                                kafka_producer.send(
                                    kafka_topic,
                                    value=json.dumps(message).encode("utf-8"),
                                    key=cam_ids[src_index].encode("utf-8")
                                )
                    except KafkaTimeoutError as e:
                        kafka_producer = KafkaProducer(
                            bootstrap_servers=[os.getenv("KAFKA_BROKER")],
                            request_timeout_ms=5000,
                            max_block_ms=5000,
                        )
                except Exception as e:
                    logger.error(f"Error when sending Deepstream message: {str(e)}")

            # FPS
            # Update frame rate through this probe
            stream_index = "stream{0}".format(frame_meta.pad_index)
            perf_data.update_fps(stream_index)

            try:
                l_frame = l_frame.next
            except StopIteration:
                break
        return Gst.PadProbeReturn.OK

    def sgie_src_pad_buffer_probe_ppe02(self, pad, info, u_data):
        global kafka_producer
        branch_idx = u_data["branch_idx"]
        kafka_topic = u_data["kafka_topic"]
        model_name = u_data["model_name"]
        model_id = u_data["model_id"]
        target_class_names = u_data["target_class_names_dict"].get(model_name, [])
        perf_data = getattr(self, f"perf_data_{branch_idx}")
        gst_buffer = info.get_buffer()
        if not gst_buffer:
            logger.warning("Unable to get GstBuffer")
            return
        # Retrieve batch metadata from the gst_buffer
        # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
        # C address of gst_buffer as input, which is obtained with hash(gst_buffer)

        # Enable latency measurement via probe if environment variable NVDS_ENABLE_LATENCY_MEASUREMENT=1 is set.
        # To enable component level latency measurement, please set environment variable
        # NVDS_ENABLE_COMPONENT_LATENCY_MEASUREMENT=1 in addition to the above.
        # if measure_latency1:
        #     num_sources_in_batch = pyds.nvds_measure_buffer_latency(hash(gst_buffer))
        #     if num_sources_in_batch == 0:
        #         logger.warning("Unable to get number of sources in GstBuffer for latency measurement")

        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
        l_frame = batch_meta.frame_meta_list

        while l_frame is not None:
            try:
                frame_meta = pyds.glist_get_nvds_frame_meta(l_frame.data)
                src_index = frame_meta.pad_index
            except StopIteration:
                break

            frame_number = frame_meta.frame_num

            if frame_number % (frame_interval + 1) == 0:
                # print(f"src_index={src_index} Frame Number={frame_number}")
                l_obj = frame_meta.obj_meta_list

                detections = []

                while l_obj is not None:
                    try:
                        # Casting l_obj.data to pyds.NvDsObjectMeta
                        obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
                        unique_component_id = obj_meta.unique_component_id
                        class_id = obj_meta.class_id
                        obj_confidence = obj_meta.confidence
                        obj_label = obj_meta.obj_label
                        rect_params = obj_meta.rect_params
                        x1 = int(rect_params.left)
                        y1 = int(rect_params.top)
                        x2 = int(x1 + rect_params.width)
                        y2 = int(y1 + rect_params.height)

                        # Skip if object is not in target
                        if len(target_class_names) and not obj_label in target_class_names:
                            try:
                                l_obj = l_obj.next
                                continue
                            except StopIteration:
                                break

                        # Skip if confidence is too small
                        if obj_confidence < 0:
                            try:
                                l_obj = l_obj.next
                                continue
                            except StopIteration:
                                break

                        unknown_prob = 0.0
                        not_safety_prob = 0.0
                        safety_prob = 0.0
                        classifier_meta_list = obj_meta.classifier_meta_list
                        while classifier_meta_list is not None:
                            try:
                                class_meta = pyds.NvDsClassifierMeta.cast(
                                    classifier_meta_list.data
                                )
                            except StopIteration:
                                break
                            l_label = class_meta.label_info_list
                            while l_label is not None:
                                try:
                                    label_info = pyds.NvDsLabelInfo.cast(
                                        l_label.data
                                    )
                                except StopIteration:
                                    break

                                if label_info.result_label == "unknown":
                                    unknown_prob = label_info.result_prob
                                elif label_info.result_label == "not_safety_shoes":
                                    not_safety_prob = label_info.result_prob
                                elif label_info.result_label == "safety_shoes":
                                    safety_prob = label_info.result_prob
                                if (
                                        unknown_prob != 0 or not_safety_prob != 0 or safety_prob != 0
                                ):
                                    # has_event_trigger = True
                                    now_time = datetime.now().strftime(
                                        "%d/%m/%y %H:%M:%S"
                                    )
                                    # print(
                                    #     f"{now_time} Result: cam_id={cam_ids[src_index]} obj_label={obj_label}  label={label_info.result_label}  prob={label_info.result_prob}"
                                    # )

                                try:
                                    l_label = l_label.next
                                except StopIteration:
                                    break

                            try:
                                classifier_meta_list = classifier_meta_list.next
                            except StopIteration:
                                break

                        predicted_class = "unknown"
                        predicted_prob = 0.0
                        mapping = {"unknown": unknown_prob,
                                   "not_safety_shoes": not_safety_prob,
                                   "safety_shoes": safety_prob}
                        for k, v in mapping.items():
                            if v > 0.0:
                                predicted_class = k
                                predicted_prob = v
                                break

                        detection = {
                            "xyxy": [x1, y1, x2, y2],
                            "confidence": obj_confidence,
                            "class_id": class_id,
                            "class_name": obj_label,
                            "detect_time": datetime.now(timezone.utc).timestamp(),
                            "video_url": cam_sources[src_index],
                            "cam_id": cam_ids[src_index],
                            "frame_id": frame_number,
                            "classifier": predicted_class,
                            "classifier_prob": predicted_prob,
                            "push_time": datetime.now(timezone.utc).timestamp()
                        }
                        if model_id == unique_component_id:
                            detections.append(detection)

                    except StopIteration:
                        break

                    except Exception as e:
                        print(e)
                        break

                    try:
                        l_obj = l_obj.next
                    except StopIteration:
                        break

                try:
                    message = {
                        "cam_id": cam_ids[src_index],
                        "frame_id": frame_number,
                        "detections": detections,
                        "video_url": cam_sources[src_index],
                        "push_time": datetime.now(timezone.utc).timestamp(),
                        "extra_information": extra_informations[src_index]
                    }

                    # print(message)

                    try:
                        allow_kafka_topics = self.camera_topics_mapping.get(self.cam_ids[src_index])
                        if allow_kafka_topics :
                            if model_name in allow_kafka_topics:
                                kafka_producer.send(
                                    kafka_topic,
                                    value=json.dumps(message).encode("utf-8"),
                                    key=cam_ids[src_index].encode("utf-8")
                                )
                    except KafkaTimeoutError as e:
                        kafka_producer = KafkaProducer(
                            bootstrap_servers=[os.getenv("KAFKA_BROKER")],
                            request_timeout_ms=5000,
                            max_block_ms=5000,
                        )
                except Exception as e:
                    print(f"---- {src_index}")
                    print(e)

            # FPS
            # Update frame rate through this probe
            stream_index = "stream{0}".format(frame_meta.pad_index)
            perf_data.update_fps(stream_index)

            try:
                l_frame = l_frame.next
            except StopIteration:
                break
        return Gst.PadProbeReturn.OK

    def sgie_src_pad_buffer_probe_par(self, pad, info, u_data):
        global kafka_producer
        branch_idx = u_data["branch_idx"]
        kafka_topic = u_data["kafka_topic"]
        model_name = u_data["model_name"]
        model_id = u_data["model_id"]
        target_class_names = u_data["target_class_names_dict"].get(model_name, [])
        perf_data = getattr(self, f"perf_data_{branch_idx}")
        gst_buffer = info.get_buffer()
        if not gst_buffer:
            logger.warning("Unable to get GstBuffer")
            return
        # Retrieve batch metadata from the gst_buffer
        # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
        # C address of gst_buffer as input, which is obtained with hash(gst_buffer)

        # Enable latency measurement via probe if environment variable NVDS_ENABLE_LATENCY_MEASUREMENT=1 is set.
        # To enable component level latency measurement, please set environment variable
        # NVDS_ENABLE_COMPONENT_LATENCY_MEASUREMENT=1 in addition to the above.
        # if measure_latency1:
        #     num_sources_in_batch = pyds.nvds_measure_buffer_latency(hash(gst_buffer))
        #     if num_sources_in_batch == 0:
        #         logger.warning("Unable to get number of sources in GstBuffer for latency measurement")

        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
        l_frame = batch_meta.frame_meta_list

        while l_frame is not None:
            try:
                frame_meta = pyds.glist_get_nvds_frame_meta(l_frame.data)
                src_index = frame_meta.pad_index
            except StopIteration:
                break

            frame_number = frame_meta.frame_num

            if frame_number % (frame_interval + 1) == 0:
                l_obj = frame_meta.obj_meta_list

                detections = []

                while l_obj is not None:
                    try:
                        # Casting l_obj.data to pyds.NvDsObjectMeta
                        obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
                        unique_component_id = obj_meta.unique_component_id
                        class_id = obj_meta.class_id
                        obj_confidence = obj_meta.confidence
                        obj_label = obj_meta.obj_label
                        rect_params = obj_meta.rect_params
                        x1 = int(rect_params.left)
                        y1 = int(rect_params.top)
                        x2 = int(x1 + rect_params.width)
                        y2 = int(y1 + rect_params.height)

                        # Skip if object is not in target
                        if len(target_class_names) and not obj_label in target_class_names:
                            try:
                                l_obj = l_obj.next
                                continue
                            except StopIteration:
                                break

                        # Skip if confidence is too small
                        if obj_confidence < 0:
                            try:
                                l_obj = l_obj.next
                                continue
                            except StopIteration:
                                break

                        use_phone_prob = 0.0
                        attach_phone_prob = 0.0
                        classifier_meta_list = obj_meta.classifier_meta_list
                        while classifier_meta_list is not None:
                            try:
                                class_meta = pyds.NvDsClassifierMeta.cast(
                                    classifier_meta_list.data
                                )
                            except StopIteration:
                                break
                            l_label = class_meta.label_info_list
                            while l_label is not None:
                                try:
                                    label_info = pyds.NvDsLabelInfo.cast(
                                        l_label.data
                                    )
                                except StopIteration:
                                    break

                                if label_info.result_label == "using_phone":
                                    use_phone_prob = label_info.result_prob
                                elif label_info.result_label == "attach_phone":
                                    attach_phone_prob = label_info.result_prob

                                if (
                                        attach_phone_prob != 0
                                        or use_phone_prob != 0
                                ):
                                    # has_event_trigger = True
                                    now_time = datetime.now().strftime(
                                        "%d/%m/%y %H:%M:%S"
                                    )
                                    # logger.info(
                                    #     f"{now_time} Result: cam_id={cam_ids[src_index]} obj_label={obj_label}  label={label_info.result_label}  prob={label_info.result_prob}"
                                    # )

                                try:
                                    l_label = l_label.next
                                except StopIteration:
                                    break

                            try:
                                classifier_meta_list = classifier_meta_list.next
                            except StopIteration:
                                break

                        detection = {
                            "xyxy": [x1, y1, x2, y2],
                            "confidence": obj_confidence,
                            "class_id": class_id,
                            "class_name": obj_label,
                            "detect_time": datetime.now(timezone.utc).timestamp(),
                            "video_url": cam_sources[src_index],
                            "cam_id": cam_ids[src_index],
                            "frame_id": frame_number,
                            "using_phone_scores": float(use_phone_prob),
                            "attach_phone_scores": float(attach_phone_prob),
                            "push_time": datetime.now(timezone.utc).timestamp(),
                        }
                        if model_id == unique_component_id:
                            detections.append(detection)

                    except StopIteration:
                        break

                    except Exception as e:
                        logger.error(f"Error when process frame: {str(e)}")
                        break

                    try:
                        l_obj = l_obj.next
                    except StopIteration:
                        break

                try:
                    message = {
                        "cam_id": cam_ids[src_index],
                        "frame_id": frame_number,
                        "detections": detections,
                        "video_url": cam_sources[src_index],
                        "push_time": datetime.now(timezone.utc).timestamp(),
                        "extra_information": extra_informations[src_index]
                    }

                    try:
                        allow_kafka_topics = self.camera_topics_mapping.get(self.cam_ids[src_index])
                        if allow_kafka_topics:
                            if model_name in allow_kafka_topics:
                                kafka_producer.send(
                                    kafka_topic,
                                    value=json.dumps(message).encode("utf-8"),
                                    key=cam_ids[src_index].encode("utf-8")
                                )
                    except KafkaTimeoutError as e:
                        kafka_producer = KafkaProducer(
                            bootstrap_servers=[os.getenv("KAFKA_BROKER")],
                            request_timeout_ms=5000,
                            max_block_ms=5000,
                        )
                except Exception as e:
                    logger.error(f"Error when sending Deepstream message: {str(e)}")

            # FPS
            # Update frame rate through this probe
            stream_index = "stream{0}".format(frame_meta.pad_index)
            perf_data.update_fps(stream_index)

            try:
                l_frame = l_frame.next
            except StopIteration:
                break
        return Gst.PadProbeReturn.OK

    def create_source_bin(self, index, uri):
        # Create a source GstBin to abstract this bin's content from the rest of the
        # pipeline
        bin_name = "source-bin-%02d" % index

        nbin = Gst.Bin.new(bin_name)
        if not nbin:
            sys.stderr.write(" Unable to create source bin \n")

        # Source element for reading from the uri.
        # We will use decodebin and let it figure out the container format of the
        # stream and the codec and plug the appropriate demux and decode plugins.
        uri_decode_bin = Gst.ElementFactory.make("uridecodebin", "uri-decode-bin")
        if not uri_decode_bin:
            sys.stderr.write("Unable to create uri decode bin \n")
        # We set the input uri to the source element
        uri_decode_bin.set_property("uri", uri)
        # uri_decode_bin.set_property("file-loop", 1)
        # Connect to the "pad-added" signal of the decodebin which generates a
        # callback once a new pad for raw data has beed created by the decodebin
        uri_decode_bin.connect("pad-added", cb_newpad, nbin)
        uri_decode_bin.connect("child-added", decodebin_child_added, self.pipeline)

        # We need to create a ghost pad for the source bin which will act as a proxy
        # for the video decoder src pad. The ghost pad will not have a target right
        # now. Once the decode bin creates the video decoder and generates the
        # cb_newpad callback, we will set the ghost pad target to the video decoder
        # src pad.
        Gst.Bin.add(nbin, uri_decode_bin)
        bin_pad = nbin.add_pad(Gst.GhostPad.new_no_target("src", Gst.PadDirection.SRC))
        if not bin_pad:
            sys.stderr.write(" Failed to add ghost pad in source bin \n")
            return None
        return nbin

    # def eos_event_listener(self, client_data):
    #     logger.info("Pipeline EOS event")
    #     dsl_pipeline_stop(self.pipeline_name)
    #     dsl_main_loop_quit()

    # ##
    # # Function to be called on every change of Pipeline state
    # ##
    # def state_change_listener(self, old_state, new_state, client_data):
    #     print("previous state = ", old_state, ", new state = ", new_state)
    #     if new_state == DSL_STATE_PLAYING:
    #         dsl_pipeline_dump_to_dot(self.pipeline_name, "state-playing")
