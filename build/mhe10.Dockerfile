# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variable to ensure logs are not buffered
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY ./third_party_services/mhe10_postprocess_event_checking/* /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install wget
RUN apt-get update && apt-get install -y wget

# Make sure script is executable
RUN chmod +x download_weight.sh

# Expose port
EXPOSE 8089

# Run the weight download script before starting the app
CMD ["/bin/sh", "-c", "./download_weight.sh && uvicorn app:app --host 0.0.0.0 --port 8089"]
