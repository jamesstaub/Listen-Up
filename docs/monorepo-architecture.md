# **Cloud-Agnostic Monorepo Architecture**

This document defines the high-level architecture for our monorepo. The primary goal is to manage multiple related projects (the core app, microservices, shared libraries) within a single repository to facilitate code reuse, simplify dependency management, and ensure consistency. The architecture is designed to be cloud-agnostic, allowing us to deploy services to different platforms (AWS, GCP) without a complete refactor.

## **Core Principles**

* **Single Source of Truth:** All code lives in one place, making it easy to find and update shared components.  
* **Decoupled Services:** Although in a single repository, each service (microservice, frontend) is a self-contained unit with its own dependencies and build process.  
* **Shared Utilities:** Common code (data models, utility functions) is isolated into a shared/ directory, which other services can depend on.

## **Folder Structure**

The repository will be organized with a clear, logical structure.

my-monorepo/  
├── services/                 \# All individual services and applications  
│   ├── main\_app/             \# The Django application (backend/API)  
│   ├── audio\_analyzer/       \# Microservice for audio analysis (librosa, etc.)  
│   ├── umap\_service/         \# Microservice for on-demand UMAP computations  
│   └── ...                   \# Other microservices  
├── integrations/             \# Third-party integrations (e.g., Google Drive, Dropbox)  
│   ├── google\_drive/         \# API clients and logic for Google Drive  
│   └── dropbox/              \# API clients and logic for Dropbox  
├── shared/                   \# Common code, data models, and libraries  
│   ├── python/               \# Shared Python library  
│   │   ├── models.py         \# Data models (AudioFile, PipelineNode, etc.)  
│   │   └── utils.py          \# General utility functions  
│   └── js/                   \# Shared JavaScript library  
│       ├── constants.js  
│       └── utils.js  
└── ...

## **Service Communication**

Communication between services is decoupled via a message queue, as detailed in the microservice\_communication.md document.

## **Shared Module System**

The shared/ directory is a critical component for code reuse. Instead of each service having its own version of a data model, they all import from this single, shared source.

### **How it Works**

* **Python:** The shared/python directory will be a Python package. A microservice's Dockerfile will explicitly copy this directory into its build context. The requirements.txt file for the service will then declare a dependency on the shared module via a relative path. This ensures the microservice's final image only contains the code it needs, keeping it small and efficient.  
* **JavaScript:** The shared/js directory will contain standard ES modules. Frontend components will import these modules directly, and the build bundler (like Webpack or Rollup) will include only the necessary shared code in the final production build.

## **Third-Party Integrations**

All third-party cloud storage and API integrations will live in a dedicated integrations/ directory. This approach ensures that:

* **Isolation:** A change to the Google Drive API client doesn't affect the core main\_app or other integrations.  
* **Code Reuse:** The integrations folder can contain shared authentication and data handling logic for different providers.  
* **Abstraction:** The main\_app will interact with these integrations through a simple, unified interface, regardless of whether the user is connected to Google Drive or Dropbox. This makes it easy to add new providers in the future.