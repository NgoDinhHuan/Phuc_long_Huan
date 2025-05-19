FROM python:3.10-slim
LABEL authors="quinv"

# Install dependencies
RUN pip install docker schedule requests pydantic

# Create a directory for the application
WORKDIR /app

# Copy your Python script into the container
COPY manager.py /app/
COPY config.py /app/
COPY gateway.py /app/

CMD ["python", "manager.py"]