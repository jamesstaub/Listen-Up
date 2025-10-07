FROM --platform=linux/amd64 python:3.12

# Install system dependencies
RUN apt-get update && apt-get install -y wget tar && rm -rf /var/lib/apt/lists/*

# Install FluCoMa CLI (Linux x64 - container will run in x64 mode)
RUN wget -O /tmp/FluCoMa-CLI-Linux-x64.tar.gz https://github.com/flucoma/flucoma-cli/releases/download/1.0.9/FluCoMa-CLI-Linux-x64.tar.gz \
    && mkdir -p /opt/flucoma-cli \
    && tar -xzf /tmp/FluCoMa-CLI-Linux-x64.tar.gz -C /opt/flucoma-cli \
    && rm /tmp/FluCoMa-CLI-Linux-x64.tar.gz \
    && chmod +x /opt/flucoma-cli/FluidCorpusManipulation/bin

ENV PATH="/opt/flucoma-cli/FluCoMa-CLI-Linux-x64:$PATH"
ENV FLUCOMA_BIN_DIR="/opt/flucoma-cli/FluidCorpusManipulation/bin"

# Set up working directory
WORKDIR /app

# Copy only requirements files for dependency installation
COPY requirements/ ./requirements/
COPY microservices/flucoma_service/requirements.txt ./microservices/flucoma_service/

# Install Python dependencies
RUN pip install --no-cache-dir -r microservices/flucoma_service/requirements.txt

# Note: Source code will be mounted as volumes in docker-compose.yml
# This allows for live code updates without rebuilding the container

CMD ["python", "microservices/flucoma_service/app.py"]
