FROM python:3.12

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy only requirements files for dependency installation
COPY requirements/ ./requirements/
COPY backend/requirements.txt ./backend/

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r backend/requirements.txt

# Note: Source code will be mounted as volumes in docker-compose.yml
# This allows for live code updates without rebuilding the container

# Expose port for Flask
EXPOSE 8000

# Set Flask environment variables
ENV FLASK_APP=backend/app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=8000

# Run the Flask app
CMD ["python", "-m", "flask", "run"]