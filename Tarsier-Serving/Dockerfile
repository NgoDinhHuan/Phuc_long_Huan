FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel-ubuntu22.04

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive



# Set non-interactive mode for apt-get
ENV DEBIAN_FRONTEND=noninteractive 

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install torch==2.3.0
RUN pip install flash-attn==2.7.0.post2
# Install Miniconda (if not included in the base image)

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app
RUN pip install  -r requirements.txt



# Copy application code
COPY app.py /app



# Activate the conda environment at runtime and start uvicorn
ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
