import sys
sys.path.append('../')
from os import environ
import os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst
from ctypes import *
import time
import sys
import math
from utils.bus_call import bus_call
from utils.FPS import PERF_DATA
from src.models.input_data import InputData
from datetime import datetime
import json

import pyds

from kafka import KafkaProducer
from kafka.errors import KafkaTimeoutError

from loguru import logger

Gst.debug_set_default_threshold(2) # (0: error, 1: warning, 2: info, 3: debug, 4: verbose)


perf_data = None
measure_latency = False

cam_sources = []
cam_ids = []
extra_informations = []

BATCH_SIZE_TRITON = int(os.getenv("BATCH_SIZE_TRITON", default=16))
frame_interval = int(os.getenv("FRAME_PROCESS_INTERVAL", default=1))

target_class_names = os.getenv("TARGET_CLASS_NAMES", default="")
if target_class_names:
    target_class_names = target_class_names.split(',')

MAX_DISPLAY_LEN=64
MUXER_BATCH_TIMEOUT_USEC = 33000
TILED_OUTPUT_WIDTH=1920
TILED_OUTPUT_HEIGHT=1080
OSD_PROCESS_MODE= 0
OSD_DISPLAY_TEXT= 1
fps_log_interval = 10000

try:
    kafka_producer = KafkaProducer(
        bootstrap_servers=[os.getenv("KAFKA_BROKER")],
        request_timeout_ms=5000,
        max_block_ms=5000,
    )
except Exception as e:
    logger.error(f"Init Kafka error: {str(e)}")
    exit()

# pgie_src_pad_buffer_probe  will extract metadata received on tiler sink pad
# and update params for drawing rectangle, object information etc.
def pgie_src_pad_buffer_probe(pad,info,u_data):
    global kafka_producer, perf_data, measure_latency
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
    if measure_latency:
        num_sources_in_batch = pyds.nvds_measure_buffer_latency(hash(gst_buffer))
        if num_sources_in_batch == 0:
            logger.warning("Unable to get number of sources in GstBuffer for latency measurement")

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
                        "detect_time": time.time(),
                        "video_url": cam_sources[src_index],
                        "cam_id": cam_ids[src_index],
                        "frame_id": frame_number,
                        "push_time": datetime.now().strftime(
                            "%d/%m/%y %H:%M:%S"
                        ),
                        "extra_information": extra_informations[src_index],
                    }
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
                if len(detections):
                    message = {
                        "cam_id": cam_ids[src_index],
                        "frame_id": frame_number,
                        "detections": detections,
                        "video_url": cam_sources[src_index],
                        "push_time": datetime.now().strftime(
                            "%d/%m/%y %H:%M:%S"
                        ),
                        "extra_information": extra_informations[src_index],
                    }

                    try:
                        kafka_producer.send(
                            os.getenv("KAFKA_DEEPSTREAM_TOPIC"),
                            json.dumps(message).encode("utf-8"),
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



def cb_newpad(decodebin, decoder_src_pad,data):
    caps=decoder_src_pad.get_current_caps()
    if not caps:
        caps = decoder_src_pad.query_caps()
    gststruct=caps.get_structure(0)
    gstname=gststruct.get_name()
    source_bin=data
    features=caps.get_features(0)

    # Need to check if the pad created by the decodebin is for video and not
    # audio.
    if(gstname.find("video")!=-1):
        # Link the decodebin pad only if decodebin has picked nvidia
        # decoder plugin nvdec_*. We do this by checking if the pad caps contain
        # NVMM memory features.
        if features.contains("memory:NVMM"):
            # Get the source bin ghost pad
            bin_ghost_pad=source_bin.get_static_pad("src")
            if not bin_ghost_pad.set_target(decoder_src_pad):
                sys.stderr.write("Failed to link decoder src pad to source bin ghost pad\n")
        else:
            sys.stderr.write(" Error: Decodebin did not pick nvidia decoder plugin.\n")

def decodebin_child_added(child_proxy,Object,name,user_data):
    if(name.find("decodebin") != -1):
        Object.connect("child-added",decodebin_child_added,user_data)

    if "source" in name:
        source_element = child_proxy.get_by_name("source")
        if source_element.find_property('drop-on-latency') != None:
            Object.set_property("drop-on-latency", True)



def create_source_bin(index,uri):
    # Create a source GstBin to abstract this bin's content from the rest of the
    # pipeline
    bin_name="source-bin-%02d" %index

    nbin=Gst.Bin.new(bin_name)
    if not nbin:
        sys.stderr.write(" Unable to create source bin \n")

    # Source element for reading from the uri.
    # We will use decodebin and let it figure out the container format of the
    # stream and the codec and plug the appropriate demux and decode plugins.
    uri_decode_bin=Gst.ElementFactory.make("uridecodebin", "uri-decode-bin")
    if not uri_decode_bin:
        sys.stderr.write(" Unable to create uri decode bin \n")
    # We set the input uri to the source element
    uri_decode_bin.set_property("uri",uri)
    # Connect to the "pad-added" signal of the decodebin which generates a
    # callback once a new pad for raw data has beed created by the decodebin
    uri_decode_bin.connect("pad-added",cb_newpad,nbin)
    uri_decode_bin.connect("child-added",decodebin_child_added,nbin)

    # We need to create a ghost pad for the source bin which will act as a proxy
    # for the video decoder src pad. The ghost pad will not have a target right
    # now. Once the decode bin creates the video decoder and generates the
    # cb_newpad callback, we will set the ghost pad target to the video decoder
    # src pad.
    Gst.Bin.add(nbin,uri_decode_bin)
    bin_pad=nbin.add_pad(Gst.GhostPad.new_no_target("src",Gst.PadDirection.SRC))
    if not bin_pad:
        sys.stderr.write(" Failed to add ghost pad in source bin \n")
        return None
    return nbin

def run(inputs: InputData, requested_pgie=None, disable_probe=False):
    global perf_data, cam_ids, cam_sources, extra_informations
    cam_sources = inputs.get_src()
    cam_ids = inputs.get_cams_id()
    extra_informations = inputs.get_extra_informations()
    perf_data = PERF_DATA(inputs.get_size())
    config = os.getenv('PGIE_CONFIG_FILE_PATH')

    number_sources=inputs.get_size()

    # Standard GStreamer initialization
    Gst.init(None)

    ##################################
    # Create gstreamer elements
    ##################################
    # Create Pipeline
    pipeline = Gst.Pipeline()
    is_live = False
    if not pipeline:
        sys.stderr.write(" Unable to create Pipeline \n")


    # Create nvstreammux
    streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
    if not streammux:
        sys.stderr.write(" Unable to create NvStreamMux \n")
    pipeline.add(streammux)

    # Create sources
    for i in range(number_sources):
        uri_name=cam_sources[i]
        if uri_name.find("rtsp://") == 0 :
            is_live = True
        source_bin=create_source_bin(i, uri_name)
        if not source_bin:
            sys.stderr.write("Unable to create source bin \n")
        pipeline.add(source_bin)
        padname="sink_%u" %i
        sinkpad= streammux.request_pad_simple(padname)
        if not sinkpad:
            sys.stderr.write("Unable to create sink pad bin \n")
        srcpad=source_bin.get_static_pad("src")
        if not srcpad:
            sys.stderr.write("Unable to create src pad bin \n")
        srcpad.link(sinkpad)

    # Create Queues
    queue1=Gst.ElementFactory.make("queue","queue1")
    queue2=Gst.ElementFactory.make("queue","queue2")
    queue3=Gst.ElementFactory.make("queue","queue3")
    queue4=Gst.ElementFactory.make("queue","queue4")
    queue5=Gst.ElementFactory.make("queue","queue5")
    pipeline.add(queue1)
    pipeline.add(queue2)
    pipeline.add(queue3)
    pipeline.add(queue4)
    pipeline.add(queue5)


    # Create Pgie
    if requested_pgie != None and (requested_pgie == 'nvinferserver' or requested_pgie == 'nvinferserver-grpc') :
        pgie = Gst.ElementFactory.make("nvinferserver", "primary-inference")
    elif requested_pgie != None and requested_pgie == 'nvinfer':
        pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    else:
        pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    if not pgie:
        sys.stderr.write(" Unable to create pgie :  %s\n" % requested_pgie)


    # NVDS Logger: Use nvdslogger for perf measurement instead of probe function
    nvdslogger = None
    if disable_probe:
        nvdslogger = Gst.ElementFactory.make("nvdslogger", "nvdslogger")


    # Create tiler
    tiler=Gst.ElementFactory.make("nvmultistreamtiler", "nvtiler")
    if not tiler:
        sys.stderr.write(" Unable to create tiler \n")


    # Create Video Converter
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
    if not nvvidconv:
        sys.stderr.write(" Unable to create nvvidconv \n")


    # Create OSD
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
    if not nvosd:
        sys.stderr.write(" Unable to create nvosd \n")
    nvosd.set_property('process-mode',OSD_PROCESS_MODE)
    nvosd.set_property('display-text',OSD_DISPLAY_TEXT)


    # Create final Sink
    sink = Gst.ElementFactory.make("fakesink", "fakesink")
    sink.set_property('enable-last-sample', 0)
    sink.set_property('sync', 0)
    if not sink:
        sys.stderr.write(" Unable to create sink element \n")


    ##################################
    # Set properties
    ##################################
    if is_live:
        streammux.set_property('live-source', 1)

    # Streammux
    streammux.set_property('width', 1920)
    streammux.set_property('height', 1080)
    streammux.set_property('batch-size', number_sources)
    streammux.set_property('batched-push-timeout', MUXER_BATCH_TIMEOUT_USEC)

    # Pgie
    if requested_pgie == "nvinferserver" and config != None:
        pgie.set_property('config-file-path', config)
    elif requested_pgie == "nvinferserver-grpc" and config != None:
        pgie.set_property('config-file-path', config)
    elif requested_pgie == "nvinfer" and config != None:
        pgie.set_property('config-file-path', config)
    else:
        pgie.set_property('config-file-path', "dstest3_pgie_config.txt")

    pgie.set_property('interval',frame_interval)
    pgie.set_property('batch-size',BATCH_SIZE_TRITON)

    pgie_batch_size=pgie.get_property("batch-size")
    if pgie_batch_size != number_sources:
        logger.warning(f"WARNING: Overriding infer-config batch-size: {pgie_batch_size} with number of sources: {number_sources}")
        pgie.set_property("batch-size",number_sources)

    # Tiler
    tiler_rows=int(math.sqrt(number_sources))
    tiler_columns=int(math.ceil((1.0*number_sources)/tiler_rows))
    tiler.set_property("rows",tiler_rows)
    tiler.set_property("columns",tiler_columns)
    tiler.set_property("width", TILED_OUTPUT_WIDTH)
    tiler.set_property("height", TILED_OUTPUT_HEIGHT)

    # Sink
    sink.set_property("qos",0)


    ##################################
    # Add elements to pipeline
    ##################################
    pipeline.add(pgie)
    if nvdslogger:
        pipeline.add(nvdslogger)
    pipeline.add(tiler)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(sink)


    ##################################
    # Link elements
    ##################################
    streammux.link(queue1)
    queue1.link(pgie)
    pgie.link(queue2)
    if nvdslogger:
        queue2.link(nvdslogger)
        nvdslogger.link(tiler)
    else:
        queue2.link(tiler)
    tiler.link(queue3)
    queue3.link(nvvidconv)
    nvvidconv.link(queue4)
    queue4.link(nvosd)
    nvosd.link(queue5)
    queue5.link(sink)



    #####################################

    # create an event loop and feed gstreamer bus mesages to it
    loop = GLib.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)
    pgie_src_pad=pgie.get_static_pad("src")

    if not pgie_src_pad:
        sys.stderr.write(" Unable to get src pad \n")
    else:
        if not disable_probe:
            pgie_src_pad.add_probe(Gst.PadProbeType.BUFFER, pgie_src_pad_buffer_probe, 0)
            # perf callback function to print fps every 5 sec
            timeout_id = GLib.timeout_add(fps_log_interval, perf_data.perf_print_callback)
    # Enable latency measurement via probe if environment variable NVDS_ENABLE_LATENCY_MEASUREMENT=1 is set.
    # To enable component level latency measurement, please set environment variable
    # NVDS_ENABLE_COMPONENT_LATENCY_MEASUREMENT=1 in addition to the above.
    if environ.get('NVDS_ENABLE_LATENCY_MEASUREMENT') == '1':
        logger.info ("Pipeline Latency Measurement enabled!\nPlease set env var NVDS_ENABLE_COMPONENT_LATENCY_MEASUREMENT=1 for Component Latency Measurement")
        global measure_latency
        measure_latency = True


    # start play back and listed to events
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass

    # Remove callback
    if timeout_id:
        GLib.source_remove(timeout_id)

    pipeline.set_state(Gst.State.NULL)
