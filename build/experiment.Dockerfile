# Use the official Python 3.11 image as the base
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /

# COPY ./build/requirements.vhe1.txt /requirements.txt
COPY ./build/cloud.requirements /requirements.txt


# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y
RUN apt install libx264-dev
RUN apt install x264 -y
RUN rm -rf /var/lib/apt/lists/*
RUN pip install ultralytics
# RUN pip install imageio[ffmpeg]
