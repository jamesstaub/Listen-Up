FROM python:3.12

# Install system dependencies
RUN apt-get update && apt-get install -y wget tar && rm -rf /var/lib/apt/lists/*


# Install FluCoMa CLI
RUN wget -O /tmp/FluCoMa-CLI-Linux-x64.tar.gz https://github.com/flucoma/flucoma-cli/releases/download/1.0.9/FluCoMa-CLI-Linux-x64.tar.gz \
    && mkdir -p /opt/flucoma-cli \
    && tar -xzf /tmp/FluCoMa-CLI-Linux-x64.tar.gz -C /opt/flucoma-cli \
    && rm /tmp/FluCoMa-CLI-Linux-x64.tar.gz \
    && chmod +x /opt/flucoma-cli/FluidCorpusManipulation/bin

ENV PATH="/opt/flucoma-cli/FluCoMa-CLI-Linux-x64:$PATH"
ENV FLUCOMA_BIN_DIR="/opt/flucoma-cli/FluidCorpusManipulation/bin"

# Copy microservice code and shared modules
WORKDIR /app
COPY microservices/flucoma_service/app.py ./
COPY requirements/ ./requirements/
COPY microservices/flucoma_service/requirements.txt ./flucoma_service/
# Copy both shared directories to avoid name collisions
COPY shared /app/shared
COPY microservices/shared /app/microservices_shared

RUN pip install --no-cache-dir -r flucoma_service/requirements.txt

CMD ["python", "app.py"]
