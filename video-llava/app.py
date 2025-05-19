import av
import io
import time
import uuid
import torch
import numpy as np

from functools import lru_cache
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from transformers import VideoLlavaProcessor, VideoLlavaForConditionalGeneration, BitsAndBytesConfig

from loguru import logger


app = FastAPI()
requests_status = {}
quantization_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)

model_id = "LanguageBind/Video-LLaVA-7B-hf"



# Cache the model and processor
@lru_cache()
def get_processor_and_model():
    """
    Retrieves the VideoLlava processor and model.

    Returns:
        Tuple: A tuple containing the VideoLlava processor and model.
    """
    processor = VideoLlavaProcessor.from_pretrained(model_id)
    model = VideoLlavaForConditionalGeneration.from_pretrained(
        model_id, quantization_config=quantization_config, device_map="auto"
    )
    return processor, model

processor, model = get_processor_and_model()


def read_video_pyav(container, indices):
    """
    Decode the video with PyAV decoder.

    Args:
        container (av.container.input.InputContainer): PyAV container.
        indices (List[int]): List of frame indices to decode.

    Returns:
        np.ndarray: np array of decoded frames of shape (num_frames, height, width, 3).
    """
    frames = []
    container.seek(0)
    start_index = indices[0]
    end_index = indices[-1]
    for i, frame in enumerate(container.decode(video=0)):
        if i > end_index:
            break
        if i >= start_index and i in indices:
            frames.append(frame)
    return np.stack([x.to_ndarray(format="rgb24") for x in frames])


async def process_video_task(request_id: str, query: str, file_content: bytes):
    try:
        prompt = f"USER: <video>\n{query} ASSISTANT:"
        container = av.open(io.BytesIO(file_content))
        total_frames = container.streams.video[0].frames
        indices = np.arange(0, total_frames, total_frames / 8).astype(int)
        clip = read_video_pyav(container, indices)
        inputs = processor(text=prompt, videos=clip, return_tensors="pt").to(model.device)
        generate_ids = model.generate(**inputs, max_length=512)
        response_text = processor.batch_decode(
            generate_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        assistant_text = (
            response_text.split("ASSISTANT:")[1].strip()
            if "ASSISTANT:" in response_text
            else response_text
        )

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