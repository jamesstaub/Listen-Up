# **Product Development Roadmap**

This document outlines a phased approach to the development of the audio processing application. It breaks down the project into a foundational setup, a Minimum Viable Product (MVP) for initial launch, and a roadmap for future, more complex features.

## **Phase 1: Foundational Setup (Month 1\)**

This phase focuses on building the core infrastructure and boilerplate code. The goal is to establish a stable and scalable platform that all future features will be built upon.

* **Monorepo and Docker Setup:** Configure the top-level monorepo with dedicated directories for the frontend, backend, and microservices. Create docker-compose.yml to orchestrate the services and establish a local development environment.  
* **Dual-Database Integration:** Set up the two-database system. Implement a user service on the backend to handle basic SQL-based user authentication and account management. Integrate a NoSQL database (e.g., MongoDB) to store the flexible pipelines and audio\_assets data models.  
* **Basic API & Frontend Scaffolding:** Create a simple REST API on the backend for user authentication and managing basic file uploads. Build the core React application with the main page, a basic file upload component, and a placeholder for the workflow canvas.  
* **Core Microservice Boilerplate:** Create a basic Python Flask microservice that can receive a simple job request and return a completion status. This will serve as a template for all future services.  
* **Initial Core Feature:** Implement a single, self-contained librosa-hpss microservice that can be triggered by a direct API call from the backend. The output will be stored locally in the temporary storage to validate the data flow.  
* **System Constraints & Security:** Implement foundational limits to manage cloud resource usage and prevent abuse.  
  * **Job Time Limits:** Enforce a hard time limit on all jobs at the queue or microservice level. If a job exceeds this limit (e.g., 5 minutes for the MVP), it will be automatically terminated, and the user will be notified of the failure.  
  * **Pre-computation Warnings:** The frontend will perform a "pre-flight check" based on file size and estimated complexity. For large files, a modal will warn the user that the job may time out and ask for their confirmation before submission.  
  * **Resource Throttling:** Implement rate limiting on the backend to prevent a single user from submitting a high volume of jobs. This can be done by limiting the number of concurrent jobs per user.

## **Phase 2: MVP Feature Set (Months 2-4)**

The goal of the MVP is to deliver a complete, end-to-end workflow that provides clear value to the user. This will be the first version of the application available to the public.

* **Web-based File Upload:** Implement the core functionality for users to upload a single audio file from their local machine. Handle the file storage in a temporary cloud bucket.  
* **Pipeline Canvas UI:** Develop a basic, interactive drag-and-drop flowchart UI for the user to connect nodes. The initial set of nodes will be limited to:  
  * **Input Node:** Local file upload.  
  * **HPSS Node:** Runs the librosa-hpss microservice.  
  * **MFCC Node:** Runs a new librosa-mfcc microservice to analyze a file.  
  * **Output Node:** Renders the results and provides a download link.  
* **Waveform Visualization:** Integrate a JavaScript library to render a visual waveform of the audio file in the UI.  
* **Data Serialization & Deserialization:** Ensure that the AudioFile and AudioDescriptor primitives can be correctly serialized and passed between the frontend, backend, and microservices.  
* **Final Output & Export:** Implement the logic to package the final harmonic and percussive audio files into a ZIP archive and provide a download link to the user.

## **Phase 3: Validation Criteria**

Success will be measured by a combination of quantitative and qualitative metrics.

* **User Adoption:** Achieve a target number of registered users (e.g., 500\) within the first month of launch.  
* **Workflow Completion Rate:** Maintain a high success rate (e.g., \> 95%) for all submitted jobs to ensure reliability.  
* **User Feedback:** Gather feedback on the UI/UX and core features through in-app surveys or a community forum.  
* **Performance Metrics:** Monitor job queue times and processing times to ensure the microservices are performing within acceptable limits (e.g., HPSS job completes in under 2 minutes).

## **Phase 4: Future Roadmap & Complex Features**

Once the MVP is validated, these features will be added to expand the application's capabilities. They are organized by theme.

* **Advanced Analysis & Data Science Features:**  
  * **Expanded Analysis Library:** Add new nodes for advanced algorithms like onset detection, timbre analysis, and beat tracking.  
  * **Vector Search & Similarity:** Implement a dedicated vector database to allow users to perform powerful similarity searches on their audio corpora based on descriptors like MFCCs.  
  * **Interactive Corpus Visualization:** Introduce on-demand computation for creating temporary, interactive views of large datasets. This will include a UMAP microservice to visualize the relationships between audio files in a 2D plot, allowing users to visually explore and filter their sound libraries.  
* **External Integrations:**  
  * **Cloud Storage:** Implement OAuth flows for Google Drive and Dropbox, allowing users to select and process files directly from their own cloud storage.  
  * **Google Colab GPU Integration:** Implement the full end-to-end workflow for leveraging the user's Google Colab instance for GPU-intensive jobs, like training large neural networks.  
* **Custom AI/ML Model Training:**  
  * **Custom Classifier Module:** Introduce the ClassifierModel primitive and a new train\_classifier node. The UI will allow users to label audio files and train their own custom models for sound classification.  
* **Performance & Community:**  
  * **Client-Side Processing (WASM):** Integrate a C++ WebAssembly target into the frontend for simple, in-browser analysis tasks (like basic descriptor calculation) that don't require a backend call.  
  * **Community Pipelines:** Add the ability for users to make their pipelines public. Create a community page to browse, search, and import pipelines created by other users, ranked by popularity.

## **Phase 5: Core User Experience and Operations**

This phase focuses on the fundamental aspects of the user experience and operational logistics to ensure a successful and reliable public launch.

* **User Onboarding and Authentication:** Develop a seamless, production-ready user authentication flow. This includes not just login, but also email verification for account security and a smooth onboarding process to guide new users.  
* **Real-Time Job Feedback:** Implement a real-time communication channel using **Django Channels** to push job status updates to the frontend. This will provide users with live progress on their pipelines, from "queued" to "processing" to "complete."  
* **Granular Error Handling:** Instead of simple failure messages, we will parse and present specific, user-friendly error messages from the backend, helping users understand why a job failed.  
* **File & Data Lifecycle Management:** Define and implement a clear data retention policy with a tiered approach to storage.  
  * **App-Provided Storage:** Paid users will have dedicated, long-term storage within the application's own cloud bucket. Files stored here will be immediately accessible for processing without the need for an intermediary step.  
  * **User-Provided Storage:** Free users will need to link their own Google Drive or Dropbox accounts. When a job is started, the file will be temporarily copied to a high-speed app bucket for processing. The output will then be pushed back to the user's personal cloud storage, and all intermediary files will be purged.  
  * **Temporary Files:** A separate, always-available app storage bucket will be used for all temporary files, such as those generated during a pipeline run, regardless of the user's storage tier.  
* **Monitoring and Alerting:** Set up basic monitoring for the health of all services. We will create alerts to notify developers of any issues, such as a microservice failing or the job queue backing up.