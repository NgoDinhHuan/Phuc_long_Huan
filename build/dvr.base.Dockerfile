# Use the official Python 3.11 image as the base
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /

COPY ./build/dvr.requirements /requirements.txt

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt
