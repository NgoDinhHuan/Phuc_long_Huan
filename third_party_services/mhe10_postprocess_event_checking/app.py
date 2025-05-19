import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import logging
import os

current_dir = os.path.dirname(os.path.realpath(__file__))

WEIGHT_PATH= os.path.join(current_dir, "model.pkl")
print(WEIGHT_PATH)

if not os.path.exists(WEIGHT_PATH):
    raise FileNotFoundError(f"Model file not found at {WEIGHT_PATH}")

model = joblib.load(WEIGHT_PATH)

app = FastAPI()

class Event(BaseModel):
    MHE: list
    Product: list

def compute_features(event: Event):
    IMAGE_SIZE = (1920, 1080)
    mhe, product = event.MHE, event.Product
    distances, mhe_areas, prod_areas = [], [], []

    for m, p in zip(mhe, product):
        m_bbox, p_bbox = m["bbox"], p["bbox"]
        distances.append((m_bbox[3] - p_bbox[3]) / IMAGE_SIZE[1])
        mhe_areas.append((m_bbox[2] - m_bbox[0]) * (m_bbox[3] - m_bbox[1]))
        prod_areas.append((p_bbox[2] - p_bbox[0]) * (p_bbox[3] - p_bbox[1]))
    
    while len(distances) < 5:
        distances.append(0)
        mhe_areas.append(0)
        prod_areas.append(0)
    
    return np.array(distances[:5] + mhe_areas[:5] + prod_areas[:5])

@app.post("/predict")
async def predict(event: Event):
    try:
        features = compute_features(event)
        prediction = model.predict([features])
        return {"prediction": bool(prediction[0])}
    except Exception as e:
        logging.error(f"Error during prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}