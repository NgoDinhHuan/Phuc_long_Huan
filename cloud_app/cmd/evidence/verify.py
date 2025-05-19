import asyncio
import os
import time

import requests
from loguru import logger

from cloud_app.common.config import cfg


async def verify_event_by_llava(video_path: str, event_type: str):

    if event_type == "PAR01":
        prompt = "Is the person using a phone while operating the forklift or MHE?"
    elif event_type == "PAR02":
        prompt = "Is the person using a phone?"
    elif event_type == "HM01":
        prompt = "Does the person jump off or climb onto the truck without using ladder?"
    elif event_type == "HM02":
        prompt = "Does the person climb onto the package without using ladder?"
    elif event_type == "HM03":
        prompt = "Does the person jump off or climb onto the dock?"
    elif event_type == "HM05":
        prompt = "Is the person standing on the floor?"
    elif event_type == "PPE01":
        prompt = "Is the worker not wearing safety clothing in the warehouse?"
    elif event_type == "PPE02":
        prompt = "Is the worker not wearing safety shoes?"
    elif event_type == "PRD01":
        prompt = "Are there any product boxes that have fallen on the floor?"
    elif event_type == "PL01":
        prompt = "Is someone pushing a package on the floor?"
    else:
        return True

    prompt_with_template = f'''
    Act as a warehouse supervisor and answer the following question:
    Question: {prompt}
    Respond with 'yes,' 'no,' or 'I am not sure' if the context is unclear. Do not provide explanations or additional comments.
    '''

    data = {"query": prompt_with_template}
    headers = {"accept": "application/json"}
    files = {
        "file": (
            os.path.basename(video_path),
            open(video_path, "rb"),
            "video/mp4",
        )
    }
    llava_answer = False
    t = time.time()
    try:
        logger.info(f"LLAVA_VIDEO query: {prompt}")
        response = requests.post(f"http://{cfg.llava_url}/videos/chat", headers=headers, files=files, data=data)
        request_id = response.json()["request_id"]
        logger.info(f"Request ID: {request_id}")
        count = 0
        while True:
            status_response = requests.get(f"http://{cfg.llava_url}/videos/status/{request_id}")
            status_data = status_response.json()
            if status_data["status"] == "processing" and count % 10 == 0:
                logger.info(f"LLAVA request: {request_id} is processing")

            count += 1
            if status_data["status"] == "completed":
                llava_answer = "yes" in status_data["response"].lower()
                logger.info("LLAVA_VIDEO's response: {}".format(status_data["response"]))
                logger.info("Process time: {}s".format(
                    status_data.get("completed_time", 0) - status_data.get("received_time", 0)))
                break
            elif status_data["status"] == "failed":
                logger.error("LLAVA_VIDEO failed: {}".format(status_data["error"]))
                break
            else:
                await asyncio.sleep(1)

            if time.time() - t > 60:
                logger.error("LLAVA_VIDEO response timeout")
                break

        logger.info(f"====> Number of requests: {count}")
    except Exception as e:
        logger.error(f"FAIL when query to LLAVA: {e}")


    return llava_answer
