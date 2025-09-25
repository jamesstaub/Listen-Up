# Python Environment Setup

## Quick Start (Recommended)

For full development setup with virtual environment and IDE support:

```bash
make dev
```

This single command will:
- Create a Python virtual environment (`./venv/`)
- Install all Python dependencies from the hierarchical requirements
- Create symlinks to mirror Docker container structure
- Enable proper import resolution in VS Code

## Why Virtual Environment?

### ✅ Benefits:
- **Isolated dependencies** - No conflicts with other projects
- **Reproducible environment** - Exact package versions
- **Clean system** - No pollution of global Python
- **Easy cleanup** - Just `make clean-venv`
- **Standard practice** - Industry best practice

### 🚫 Problems with Global Python:
- Dependency conflicts between projects
- System permission issues
- Hard to reproduce exact environments
- Version conflicts

## Development vs Production Import Paths

### The Challenge
In Docker containers, shared directories are copied to different locations:
- `shared/` → `/app/shared` (main shared code)
- `microservices/shared/` → `/app/microservices_shared` (microservices-only shared)

This means imports like `from microservices_shared.modules.microservice_base import MicroserviceBase` work in containers but not in local development.

### The Solution: Development Symlinks
The `make dev` command creates symlinks that mirror the container structure:

```bash
microservices_shared -> microservices/shared
```

Now these imports work identically in development and production:
```python
from microservices_shared.modules.microservice_base import MicroserviceBase
from shared.modules.assets.asset_manager_factory import create_asset_manager
```

## For Development (IDE Support)

Install all dependencies for full IDE support:

```bash
make dev
```

This creates the complete development environment:

- ✅ All dependencies installed (backend + microservices + dev tools)
- ✅ Symlinks created for proper import resolution  
- ✅ No import errors in VS Code
- ✅ Full IntelliSense and debugging support

## For Production Services

Each service installs only its required dependencies:

### Backend
```bash
pip install -r backend/requirements.txt
```

### Flucoma Microservice
```bash  
pip install -r microservices/flucoma_service/requirements.txt
```

### Librosa Microservice
```bash
pip install -r microservices/librosa_service/requirements.txt  
```

## Requirements Structure

- `requirements/base.txt` - Core shared dependencies (redis, pydantic, etc.)
- `requirements/backend.txt` - Backend-specific dependencies (flask, pymongo, etc.)
- `requirements/microservices.txt` - Common microservices dependencies
- `requirements/dev.txt` - Development tools + all service dependencies for IDE
- `requirements.txt` - Root development requirements for IDE support

### Individual Service Requirements
Each microservice has its own specific dependencies:

- `microservices/flucoma_service/requirements.txt` - FluCoMa + audio processing libs
- `microservices/librosa_service/requirements.txt` - Librosa + scipy + audio libs
- `microservices/[future_service]/requirements.txt` - Service-specific deps

## Dependency Layers

```
┌─────────────────────────────────────┐
│           dev.txt                   │  ← All deps for IDE
│  ┌─────────────────────────────────┐ │
│  │     Service-Specific            │ │  ← librosa, scipy, etc.
│  │  ┌─────────────────────────────┐ │ │
│  │  │    microservices.txt        │ │ │  ← Common microservice deps
│  │  │  ┌─────────────────────────┐ │ │ │
│  │  │  │      base.txt           │ │ │ │  ← Core shared (redis, pydantic)
│  │  │  └─────────────────────────┘ │ │ │
│  │  └─────────────────────────────┘ │ │
│  └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

## Troubleshooting & Cleanup

### Import Errors in IDE
If you see import errors like:
```
Import "microservices_shared.modules.microservice_base" could not be resolved
```

**Solution:** Run the development setup:
```bash
make dev
```

This creates the necessary symlinks for proper import resolution.

### Cleaning Development Environment
If you need to clean up the development environment:

```bash
make clean-dev    # Remove development symlinks
make clean        # Remove build artifacts and Python cache
```

### Symlink Status
To check if development symlinks are properly created:

```bash
ls -la microservices_shared
# Should show: microservices_shared -> microservices/shared
```

## VS Code Configuration

The workspace includes VS Code settings for optimal Python development:

- **Import Resolution**: Extra paths configured for all shared directories
- **Auto Imports**: Enabled for better development experience  
- **Linting**: Flake8 enabled for code quality
- **Formatting**: Black formatter configured

## Benefits

✅ **No Import Errors in IDE**: Root requirements.txt includes everything  
✅ **Optimized Docker Images**: Each service only installs what it needs  
✅ **DRY Principle**: Shared dependencies defined once in base.txt  
✅ **Clear Separation**: Easy to see what dependencies each service needs  
✅ **Scalable**: Easy to add new microservices with their own deps

## Adding a New Microservice

When adding a new microservice (e.g., `essentia_service`):

1. Create `microservices/essentia_service/requirements.txt`:
```txt
# Essentia microservice requirements
-r ../../requirements/microservices.txt

# Essentia-specific dependencies
essentia>=2.1
tensorflow>=2.8.0
```

2. Update `requirements/dev.txt` to include the new service deps for IDE support

3. The service gets microservices.txt + base.txt automatically via the `-r` reference

## Complete Developer Workflow

### New Developer Setup
```bash
# 1. Clone repository
git clone <repo-url>
cd listenup

# 2. Complete development setup (one command!)  
make dev

# 3. Open in VS Code - virtual environment and imports will work correctly
code .
```

### Daily Development
```bash
# Virtual environment automatically activates in VS Code terminal
# Work on any service - imports work everywhere
# Backend: import shared.modules.*
# Microservices: import microservices_shared.modules.*

# Test in containers when ready
make docker-up

# Clean up when needed
make clean           # Clean build artifacts
make clean-venv     # Remove virtual environment
make clean-all      # Clean everything
```

### Manual Virtual Environment Activation
If you need to run commands outside VS Code:
```bash
# Activate virtual environment
source venv/bin/activate

# Now you can run Python commands directly
python -c "import shared.modules.assets.asset_manager"
pytest
flake8

# Deactivate when done
deactivate
```

### Adding New Microservices
```bash
# 1. Create service directory and requirements.txt
mkdir microservices/new_service
echo "-r ../../requirements/microservices.txt" > microservices/new_service/requirements.txt
echo "service-specific-dep>=1.0.0" >> microservices/new_service/requirements.txt

# 2. Update dev requirements and reinstall
echo "service-specific-dep>=1.0.0" >> requirements/dev.txt
make dev

# 3. Imports work immediately:
# from microservices_shared.modules.microservice_base import MicroserviceBase
```

This setup ensures seamless development experience with zero import errors! 🎉
