# Audio Processing Application

This repository contains an audio processing application designed to provide users with tools for analyzing and manipulating audio files. The application is structured into a frontend, backend, and microservices, each serving a specific purpose in the overall architecture.

## Project Structure

```
audio-processing-app
├── frontend          # Source code for the frontend application (React)
│   ├── src          # Frontend source files
│   └── package.json  # Frontend dependencies and scripts
├── backend           # Source code for the backend application (Flask/Django)
│   ├── src          # Backend source files
│   └── requirements.txt  # Backend dependencies
├── microservices     # Microservices for audio processing
│   ├── librosa_hpss # Microservice for harmonic-percussive source separation
│   │   ├── app.py   # Implementation of the librosa-hpss microservice
│   │   └── requirements.txt  # Dependencies for librosa-hpss
│   └── librosa_mfcc # Microservice for MFCC feature extraction
│       ├── app.py   # Implementation of the librosa-mfcc microservice
│       └── requirements.txt  # Dependencies for librosa-mfcc
├── docker-compose.yml # Docker configuration for orchestration
├── Makefile          # Makefile for local installation and deployment
└── README.md         # Project documentation
```

## Getting Started

To set up the project locally, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd audio-processing-app
   ```

2. **Install dependencies:**
   - For the frontend:
     ```bash
     cd frontend
     npm install
     ```
   - For the backend:
     ```bash
     cd backend
     pip install -r requirements.txt
     ```
   - For microservices:
     - For librosa_hpss:
       ```bash
       cd microservices/librosa_hpss
       pip install -r requirements.txt
       ```
     - For librosa_mfcc:
       ```bash
       cd ../librosa_mfcc
       pip install -r requirements.txt
       ```

3. **Run the application:**
   You can use Docker to run the entire application stack:
   ```bash
   docker-compose up
   ```

## Usage

Once the application is running, you can access the frontend through your web browser. The backend and microservices will handle audio processing requests as defined in the application.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or features you would like to add.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.