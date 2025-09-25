FROM python:3.12

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*


# Copy microservice code and shared modules
WORKDIR /app
COPY microservices/librosa_service/app.py ./
COPY requirements/ ./requirements/
COPY microservices/librosa_service/requirements.txt ./librosa_service/
# Copy both shared directories to avoid name collisions
COPY shared /app/shared
COPY microservices/shared /app/microservices_shared

RUN pip install --no-cache-dir -r librosa_service/requirements.txt

CMD ["python", "app.py"]
