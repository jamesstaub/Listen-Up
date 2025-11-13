FROM python:3.12

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy only requirements files for dependency installation
COPY requirements/ ./requirements/
COPY microservices/librosa_service/requirements.txt ./microservices/librosa_service/

# Install Python dependencies  
RUN pip install --no-cache-dir -r microservices/librosa_service/requirements.txt

# Note: Source code will be mounted as volumes in docker-compose.yml
# This allows for live code updates without rebuilding the container

# Command is specified in docker-compose.yml for flexibility
