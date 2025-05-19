# Use the official Python 3.11 image as the base
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /

COPY ./build/dvr.requirements /requirements.txt

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the module files into the container
COPY dvr_app /app

WORKDIR /app

# Define the command to run your module (replace "module.py" with your actual module name)
# CMD ["python", "dvr_watchdog.py", "-d", "/usr/dvr_videos", "-b", "47.128.81.230:8003", "-t", "emagic.dvr_videos"]