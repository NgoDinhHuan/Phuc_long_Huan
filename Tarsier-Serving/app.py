from PIL import Image
import requests
import numpy as np
import av
from huggingface_hub import hf_hub_download
from transformers.configuration_utils import PretrainedConfig
from model import LlavaConfig,TarsierForConditionalGeneration
from utils import load_model_and_processor
from transformers import VideoLlavaProcessor, VideoLlavaForConditionalGeneration, BitsAndBytesConfig
import torch
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from functools import lru_cache
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import io
import time
import uuid
import torch
import numpy as np
from loguru import logger

app = FastAPI()
requests_status = {}
# Cache the model and processor
@lru_cache()
def get_processor_and_model():
    """
    Retrieves the VideoLlava processor and model.

    Returns:
        Tuple: A tuple containing the VideoLlava processor and model.
    """
    model, processor = load_model_and_processor(model_name_or_path="omni-research/Tarsier-7b", max_n_frames=8)

    return processor, model

processor, model = get_processor_and_model()


async def process_video_task(request_id: str, query: str, file_content: bytes):
    try:
        prompt = f"USER: <video>\n{query} ASSISTANT:"
        generate_kwargs = {
        "do_sample": False,
        "max_new_tokens": 512,
        "top_p": 1,
        "temperature": 0.,
        "use_cache": False
    }
        print("API Tarsier")
        inputs = processor(prompt, file_content, edit_prompt=True, return_prompt=False)
        inputs = {k:v.to(model.device) for k,v in inputs.items() if v is not None}
        outputs = model.generate(
        **inputs,
        **generate_kwargs)
        response_text = processor.tokenizer.decode(outputs[0][inputs['input_ids'][0].shape[0]:], skip_special_tokens=True)
        assistant_text = (
            response_text.split("ASSISTANT:")[1].strip()
            if "ASSISTANT:" in response_text
            else response_text
        )
        del inputs
        del outputs

        requests_status[request_id].update({"status": "completed", "response": assistant_text, "completed_time": time.time()})
        logger.info(f"Request ID: {request_id} completed, response: {assistant_text}, time: {time.time()}")

    except Exception as e:
        logger.error(f"ERROR: {e}")
        requests_status[request_id].update({"status": "failed", "error": str(e), "completed_time": time.time()})

@app.post("/videos/chat")
async def chat_with_video(query: str = Form(...), file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    file_content = await file.read()
    request_id = str(uuid.uuid4())
    requests_status[request_id] = {"status": "processing", "received_query": query, "received_time": time.time()}

    logger.info(f"Received request ID: {request_id}: {requests_status[request_id]}")

    background_tasks.add_task(process_video_task, request_id, query, file_content)
    return JSONResponse(content={"request_id": request_id, "message": "Processing in background"})


@app.get("/videos/status/{request_id}")
async def check_status(request_id: str):
    if request_id not in requests_status:
        raise HTTPException(status_code=404, detail="Request ID not found")
    response = requests_status[request_id]
    if response["status"] == "completed" or response["status"] == "failed":
        del requests_status[request_id]
        logger.info(f"Request ID: {request_id} is deleted")

    return response
