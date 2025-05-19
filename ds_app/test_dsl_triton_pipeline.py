################################################################################
#
# The example demonstrates how to create a set of Pipeline components, 
# specifically:
#   - File Source
#   - Primary Triton Inference Server (PTIS)
#   - NcDCF Low Level Tracker
#   - On-Screen Display
#   - Window Sink
# ...and how to add them to a new Pipeline and play
# 
# The example registers handler callback functions with the Pipeline for:
#   - key-release events
#   - delete-window events
#   - end-of-stream EOS events
#   - Pipeline change-of-state events
#  
################################################################################

#!/usr/bin/env python

import sys
import os
import pyds
import logging
from utils.FPS import GETFPS

sys.path.append("../")

from dsl.dsl import *

# File path for the single File Source
file_path = '/opt/nvidia/deepstream/deepstream/samples/streams/sample_720p.mp4'

# Filespec for the Primary Triton Inference Server (PTIS) config file
primary_infer_config_file = \
    'configs/pgies/yolov8/config_infer_server_primary.txt'

# Filespec for the NvDCF Tracker config file
dcf_tracker_config_file = \
    'configs/trackers/klt.txt'

# Source file dimensions are 960 × 540 - use this to set the Streammux dimensions.
SOURCE_WIDTH = 1920
SOURCE_HEIGHT = 1080

# Window Sink dimensions same as Streammux dimensions - no scaling.
sink_width = SOURCE_WIDTH
sink_height = SOURCE_HEIGHT

frame_interval = int(os.getenv("FRAME_PROCESS_INTERVAL", default=1))

fps_streams = {}

# Function to be called on End-of-Stream (EOS) event
def eos_event_listener(client_data):
    print('Pipeline EOS event')
    dsl_pipeline_stop('pipeline')
    dsl_main_loop_quit()

## 
# Function to be called on every change of Pipeline state
## 
def state_change_listener(old_state, new_state, client_data):
    print('previous state = ', old_state, ', new state = ', new_state)
    if new_state == DSL_STATE_PLAYING:
        dsl_pipeline_dump_to_dot('pipeline', "state-playing")


def custom_pad_probe_handler(buffer, user_data):
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

                    if obj_confidence > 0.5:
                        print(f"{track_id}  {class_id}  {obj_confidence} {[x1, y1, x2, y2]}")

                    # detection = {
                    #     "xyxy": [x1, y1, x2, y2],
                    #     "confidence": obj_confidence,
                    #     "track_id": track_id,
                    #     "class_id": class_id,
                    #     "class_name": obj_label,
                    #     "detect_time": time.time(),
                    #     "video_url": input_srcs_bk[src_index],
                    #     "cam_id": cams_bk[src_index],
                    #     "frame_id": frame_number,
                    #     "push_time": datetime.now().strftime(
                    #         "%d/%m/%y %H:%M:%S"
                    #     ),
                    # }
                    # detections.append(detection)

                except StopIteration:
                    break

                except Exception as e:
                    # logging.error(f"++++ list src {src_index}   --> bk: {input_srcs_bk}")
                    # logging.error(f"++++ list cam   ----> bk: {cams_bk}")
                    logging.error(e)
                    has_error = True
                    break

                # FPS
                fps_streams["stream{0}".format(src_index)].update_fps()
                if frame_number % 25 == 0:
                    fps = fps_streams["stream{0}".format(src_index)].get_fps()
                    logging.info(f"fps stream {src_index}  :  {fps}")

                try:
                    l_obj = l_obj.next
                except StopIteration:
                    break

            # try:
            #     message = {
            #         "cam_id": cams_bk[src_index],
            #         "frame_id": frame_number,
            #         "detections": detections,
            #         "video_url": input_srcs_bk[src_index],
            #         "push_time": datetime.now().strftime(
            #             "%d/%m/%y %H:%M:%S"
            #         ),
            #     }

            #     # logging.info(message)

            #     self.kafka_producer.send(
            #         os.getenv("KAFKA_DEEPSTREAM_TOPIC"),
            #         json.dumps(message).encode("utf-8"),
            #     )
            # except Exception as e:
            #     logging.error(f"---- {src_index}")
            #     logging.error(e)
            #     has_error = True

        # FPS
        fps_streams["stream{0}".format(src_index)].update_fps()
        if frame_number % 25 == 0:
            fps = fps_streams["stream{0}".format(src_index)].get_fps()
            logging.info(f"fps stream {src_index}  :  {fps}")

        try:
            l_frame = l_frame.next
        except StopIteration:
            break
    return DSL_PAD_PROBE_OK

class Component:
    def __init__(self, id: int) -> None:
        self.source_name = f"uri-source-{id}"

def main(args):

    print("========")

    # Since we're not using args, we can Let DSL initialize GST on first call
    while True:

        # # New File Source using the file path specified above, repeat diabled.
        # retval = dsl_source_file_new('file-source', file_path, False)
        # if retval != DSL_RETURN_SUCCESS:
        #     break
        
        src_elements = []
        # for idx, src in enumerate(input_srcs_bk):
        for i in range(1):
            component = Component(i)
            # New URI File Source using the filespec defined above
            # logging.info(f"{component.source_name}------------- {src}")
            retval = dsl_source_uri_new(
                component.source_name, file_path, False, False, 0
            )
            if retval != DSL_RETURN_SUCCESS:
                break
            src_elements.append(component.source_name) 
            fps_streams["stream{0}".format(i)]=GETFPS(i)   
            
        # New Primary TIS using the filespec specified above, with interval = 3
        # Note: need to set the interval to greater than 1 as the DCF Tracker
        # add a medimum level GPU computational load vs. the KTL and IOU CPU Trackers.
        retval = dsl_infer_tis_primary_new('primary-tis', primary_infer_config_file, 3)
        if retval != DSL_RETURN_SUCCESS:
            break

        # New NvDCF Tracker, setting operation width and height
        # NOTE: width and height paramaters must be multiples of 32 for dcf
        retval = dsl_tracker_new('dcf-tracker', 
            config_file = dcf_tracker_config_file,
            width = 480, 
            height = 272) 
        if retval != DSL_RETURN_SUCCESS:
            break

        # New OSD with text, clock and bbox display all enabled. 
        retval = dsl_osd_new('on-screen-display', 
            text_enabled=True, clock_enabled=True, bbox_enabled=True, mask_enabled=False)
        if retval != DSL_RETURN_SUCCESS:
            break
        
        is_file_sink = True
        if is_file_sink:
            # now_time = datetime.now().strftime("%d_%m_%yT%H_%M_%S")
            # file_name = f"/ws/ds_app/{component.source_name}_{now_time}.mkv"
            file_name = f"/ds_app/outout.mkv"
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


        # New Custom Pad Probe Handler to call Nvidia's example callback
        # for handling the Batched Meta Data
        retval = dsl_pph_custom_new(
            "custom-pph",
            client_handler=custom_pad_probe_handler,
            client_data=None,
        )
        if retval != DSL_RETURN_SUCCESS:
            break

        # Add the custom PPH to the Sink pad of the OSD
        retval = dsl_osd_pph_add(
            "on-screen-display", handler="custom-pph", pad=DSL_PAD_SINK
        )
        if retval != DSL_RETURN_SUCCESS:
            break

        src_elements.extend(
                [
                    "primary-tis",
                    "dcf-tracker",
                    "on-screen-display",
                    "final-sink",
                    None,
                ]
            )

        # Add all the components to a new pipeline
        retval = dsl_pipeline_new_component_add_many('pipeline', src_elements)
        if retval != DSL_RETURN_SUCCESS:
            break

        # Update the Pipeline's Streammux dimensions to match the source dimensions.
        retval = dsl_pipeline_streammux_dimensions_set('pipeline',
            SOURCE_WIDTH, SOURCE_HEIGHT)
        if retval != DSL_RETURN_SUCCESS:
            break

        # Add the listener callback functions defined above
        retval = dsl_pipeline_state_change_listener_add('pipeline', 
            state_change_listener, None)
        if retval != DSL_RETURN_SUCCESS:
            break
        retval = dsl_pipeline_eos_listener_add('pipeline', 
            eos_event_listener, None)
        if retval != DSL_RETURN_SUCCESS:
            break

        # Play the pipeline
        retval = dsl_pipeline_play('pipeline')
        if retval != DSL_RETURN_SUCCESS:
            break

        # Join with main loop until released - blocking call
        dsl_main_loop_run()
        retval = DSL_RETURN_SUCCESS
        break

    # Print out the final result
    print(dsl_return_value_to_string(retval))

    dsl_pipeline_delete_all()
    dsl_component_delete_all()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
