# Makefile for Audio Processing Application
# 
# This Makefile handles both development and production environments:
# - Development: Creates virtual environment + symlinks to mirror Docker container structure
# - Production: Each service installs only its required dependencies
#
# Key targets:
#   make dev     - Complete development setup with virtual environment (recommended)
#   make install - Production-style dependency installation
#   make clean   - Clean up build artifacts
#
.PHONY: all install dev venv install-dev setup-dev-env frontend backend microservices docker-up docker-down docker-restart-backend docker-restart-flucoma docker-restart-librosa docker-restart-microservices clean clean-dev clean-venv clean-all test help

# Python and virtual environment settings
VENV_DIR = venv
VENV_BIN = $(VENV_DIR)/bin
PYTHON = $(VENV_BIN)/python
PIP = $(VENV_BIN)/pip

# Default target - production-style install
all: install

# === DEVELOPMENT SETUP ===
# Complete development environment setup - this is what new developers should run

# Install development dependencies (includes all service dependencies for IDE support)
dev: venv install-dev setup-dev-env

# Create Python virtual environment
venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating Python virtual environment..."; \
		python3 -m venv $(VENV_DIR); \
		echo "Virtual environment created at $(VENV_DIR)"; \
	else \
		echo "Virtual environment already exists at $(VENV_DIR)"; \
	fi

# Install all dependencies via hierarchical requirements for full IDE support
# This installs backend + microservices + all service-specific deps + dev tools
install-dev: venv
	@echo "Installing development dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✅ All dependencies installed in virtual environment"

# Setup development environment to mirror container structure
# This creates symlinks so imports work the same in development as in Docker containers
# 
# Problem: In containers, microservices/shared is copied to /app/microservices_shared
# Solution: Create symlink microservices_shared -> microservices/shared locally  
# Result: import microservices_shared.modules.* works in both dev and containers
setup-dev-env:
	@echo "Setting up development environment..."
	@# Create symlink to mirror Docker container structure for import resolution
	@if [ ! -L microservices_shared ]; then \
		ln -sf microservices/shared microservices_shared && \
		echo "Created symlink: microservices_shared -> microservices/shared"; \
	else \
		echo "Symlink microservices_shared already exists"; \
	fi

# === PRODUCTION-STYLE INSTALLATION ===
# Install dependencies separately (useful for testing production deployment locally)
# Note: These targets assume you have activated the virtual environment manually
install: frontend backend microservices

# Install frontend dependencies (Node.js/npm)
frontend:
	cd frontend && npm install

# Install backend dependencies only (Flask app)
# Uses hierarchical requirements: backend.txt -> base.txt  
backend: venv
	$(PIP) install -r backend/requirements.txt

# Install microservices dependencies for local testing
# Each service inherits from microservices.txt -> base.txt + adds service-specific deps
microservices: venv
	$(PIP) install -r microservices/librosa_service/requirements.txt
	$(PIP) install -r microservices/flucoma_service/requirements.txt

# === DOCKER OPERATIONS ===

# Start all containers with docker-compose (backend, microservices, databases)
# Development features:
#   - Code changes in /backend and /shared auto-reload (Flask --reload)
#   - Volume mounts for live development without rebuilds
#   - Microservice code changes require container restart
# Note: If you get authentication errors, run 'docker login' first
docker-up:
	docker-compose up --build

# Stop all running containers
docker-down:
	docker-compose down

# Restart specific services after code changes
docker-restart-backend:
	docker-compose restart backend

docker-restart-flucoma:
	docker-compose restart flucoma_service

docker-restart-librosa:
	docker-compose restart librosa_service

docker-restart-microservices:
	docker-compose restart flucoma_service librosa_service

# === CLEANUP OPERATIONS ===

# Clean up build artifacts and Python cache
# Removes node_modules, Python cache files, and test artifacts
clean:
	rm -rf frontend/node_modules
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name ".pytest_cache" -type d -exec rm -rf {} +

# Clean development environment (remove symlinks created by setup-dev-env)  
# Use this if you need to reset the development environment or before switching branches
clean-dev:
	@echo "Cleaning development environment..."
	@if [ -L microservices_shared ]; then \
		rm microservices_shared && \
		echo "Removed symlink: microservices_shared"; \
	fi

# Remove virtual environment completely
clean-venv:
	@echo "Removing virtual environment..."
	@if [ -d "$(VENV_DIR)" ]; then \
		rm -rf $(VENV_DIR) && \
		echo "Removed virtual environment: $(VENV_DIR)"; \
	else \
		echo "Virtual environment not found"; \
	fi

# Complete cleanup - remove everything
clean-all: clean clean-dev clean-venv

# === TESTING ===

# Run Python tests (requires development dependencies)
test: venv
	$(PYTHON) -m pytest

# === HELP ===

# Display available targets and their descriptions
help:
	@echo "Available targets:"
	@echo ""
	@echo "=== DEVELOPMENT ==="
	@echo "  dev          - Complete development setup (venv + deps + symlinks)"
	@echo "  venv         - Create Python virtual environment only"
	@echo "  setup-dev-env - Create symlinks to mirror container structure"
	@echo "  clean-dev    - Remove development symlinks"
	@echo ""
	@echo "=== INSTALLATION ==="
	@echo "  install      - Install production dependencies separately"
	@echo "  frontend     - Install frontend dependencies only"
	@echo "  backend      - Install backend dependencies only"  
	@echo "  microservices - Install microservices dependencies only"
	@echo ""
	@echo "=== DOCKER ==="
	@echo "  docker-up              - Start all containers with docker-compose"
	@echo "  docker-down            - Stop all containers"
	@echo "  docker-restart-backend - Restart just the backend service"
	@echo "  docker-restart-flucoma - Restart just the flucoma service"
	@echo "  docker-restart-librosa - Restart just the librosa service"
	@echo "  docker-restart-microservices - Restart all microservices"
	@echo ""
	@echo "=== MAINTENANCE ==="
	@echo "  clean        - Clean up build artifacts and Python cache"
	@echo "  clean-venv   - Remove virtual environment"
	@echo "  clean-all    - Complete cleanup (artifacts + symlinks + venv)"
	@echo "  test         - Run Python tests"
	@echo "  help         - Show this help message"
	@echo ""
	@echo "🚀 Quick Start: 'make dev' for complete development setup"
	@echo "💡 Virtual Environment: All Python deps installed in ./venv/"
