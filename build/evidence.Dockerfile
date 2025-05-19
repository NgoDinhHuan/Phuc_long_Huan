# Use the official Python 3.11 image as the base
FROM emagiceyes/opencv_eme:v1

# Set the working directory in the container
WORKDIR /

COPY ./build/evidence.requirements /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY ./cloud_app/ /app/cloud_app
