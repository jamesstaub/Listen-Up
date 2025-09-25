# **Frontend Architecture**

This document specifies the architecture and core responsibilities of the frontend, a single-page application (SPA). Its primary role is to provide a responsive user interface for initiating and monitoring long-running jobs that are processed by the backend microservices.

## **1\. High-Level Overview**

The frontend will be a decoupled, client-side application. It will communicate with the backend's Processing Manager via a RESTful API and will also directly read job status from a NoSQL datastore (Firestore or MongoDB). This design ensures that the UI remains fast and responsive, as it never has to wait for a microservice to complete a task.

## **2\. Proposed Technology Stack**

For a scalable and component-driven user interface, we'll use a modern JavaScript framework.

* **Framework:** **React** will serve as the foundation for the UI. Its component-based architecture is ideal for building modular and reusable UI elements.  
* **State Management:** To manage the complex state of a multi-step pipeline, a predictable state management library like **Zustand** or **Redux** will be used. This will handle the loading state, pipeline data, and error messages in a centralized store.  
* **Styling:** A utility-first CSS framework like **Tailwind CSS** will be used for rapid and consistent styling, ensuring a clean and professional look.  
* **APIs:** We'll use the native fetch API for all communication.

## **3\. The Two-State Model: Definition vs. Execution**

To handle the complexity of both pipeline composition and job monitoring, the frontend will manage two distinct, but related, types of data in the NoSQL datastore.

### **3.1 Pipeline Definitions (The Template)**

This is a **persistent, server-side document** that defines a reusable sequence of operations and parameters. A user can save and load these definitions, making them the source of truth for the composition UI.

* **Purpose:** To save and reuse a specific pipeline configuration.  
* **Source:** User interaction with the UI (saving, loading).  
* **Data:** A document containing the pipeline array, including operation names and their parameters. A new addition is the ability for a parameter to be an input file reference, as shown below:

{  
  "pipeline\_definition\_id": "pipeline\_def-456",  
  "name": "My Ampslice & MFCC Pipeline",  
  "pipeline": \[  
    {  
      "step\_id": "step\_0",  
      "operation": "ampslice",  
      "parameters": {  
        "input": {  
          "type": "file\_id",  
          "value": "file\_xyz-789"  
        },  
        "threshold": 0.5  
      }  
    },  
    {  
      "step\_id": "step\_1",  
      "operation": "mfcc",  
      "parameters": {  
        "input": {  
          "type": "previous\_step\_id",  
          "value": "step\_0"  
        },  
        "num\_coefficients": 13  
      }  
    }  
  \]  
}

### **3.2 Job Executions (The Running Job)**

This is a **persistent, server-side document** that represents a single, active processing job. It is the single source of truth for the job's real-time status and progress.

* **Purpose:** To provide a real-time view of a running job's progress.  
* **Source:** The backend's Processing Manager and the microservices as they execute each step.  
* **Data:** The full job document, including the overall status (pending, in\_progress, completed, failed), and the status of each step within the pipeline. Each execution document will also contain a reference to the pipeline\_definition\_id it was created from.

To support previewing, the Job Execution document will be enhanced with a structured step\_outputs array that maps to the steps in the pipeline definition.

{  
  "job\_id": "job\_abc-123",  
  "pipeline\_definition\_id": "pipeline\_def-456",  
  "status": "in\_progress",  
  "step\_outputs": \[  
    {  
      "step\_id": "step\_0",  
      "operation": "ampslice",  
      "status": "completed",  
      "output\_file\_id": "file\_def-321",  
      "timestamp": "2025-05-10T12:00:00Z"  
    },  
    {  
      "step\_id": "step\_1",  
      "operation": "mfcc",  
      "status": "in\_progress",  
      "output\_file\_id": null  
    }  
  \]  
}

## **4\. Data Flow and Real-time Status Updates**

The core of the frontend's architecture is its ability to provide real-time job status without polling the main backend.

1. **Pipeline Loading & Audio Source Selection:** When the user navigates to the composition view, the frontend fetches a list of the user's saved **pipeline definitions** from the datastore. Additionally, it makes a GET request to the backend's /api/v1/files endpoint to retrieve a list of all previously processed audio files for the user. This data is used to populate a dropdown menu in the UI. The user can then select an audio file from this list or use a drag-and-drop interface to upload a new one.  
2. **Pipeline Construction:** The user can either load an existing definition or build a new one from scratch. All modifications happen in the frontend's local state.  
3. **Pipeline Saving:** The user can save their new or updated pipeline by sending a POST or PUT request to the backend's API. This persists the **pipeline definition** in the datastore.  
4. **Job Initiation:** When the user clicks "Run Job," the frontend sends a POST request to the backend's Processing Manager API at /api/v1/jobs. The payload includes the input\_file\_id and the pipeline\_definition\_id of the template they want to run.  
5. **Job ID Retrieval:** The backend responds with a job\_id and a status of pending. The frontend immediately updates its local state to reflect the new, pending job.  
6. **Real-time Monitoring:** The frontend sets up a polling loop that sends a GET request to the datastore's API at /api/v1/jobs/{job\_id} at a regular, configurable interval (e.g., every 2-3 seconds).  
7. **UI Updates and Previewing:** Upon receiving a response, the frontend updates its state with the latest job document from the datastore. The UI components, specifically the **Pipeline Composer**, react to this state change. For each step in the pipeline, the frontend will check the step\_outputs array for a matching step\_id and a status of "completed." If found, it will use the output\_file\_id to request the file from the backend's API and render a preview. This allows for live updates and a canvas-like preview for each step as it completes.  
8. **Completion:** When the job document's overall status is completed or failed, the polling loop is terminated, and the final state is rendered on the UI.

This updated polling pattern, leveraging the shared datastore as the single source of truth for job status, prevents the backend from becoming a bottleneck and ensures the user always has up-to-date information.

## **5\. Key UI Components**

The application will be built from a set of modular, reusable components.

* **Pipeline Composer:** A dedicated component for selecting an input file and composing or loading a pipeline. This component will manage the local state for a **pipeline definition** and handle saving it to the datastore. Crucially, it will also contain sub-components for each step, which will render the output preview.  
* **Audio Source Selector:** A new component responsible for handling the two primary input methods. It will feature a drag-and-drop area for local files and a dropdown list populated with a user's previously processed file IDs.  
* **Job Dashboard:** A main view that displays a list of all jobs for the current user. Each job in the list is a mini-card showing its job\_id, status, and a progress bar.  
* **Job Details:** A detailed view for a single job, showing the full pipeline with each step's status, progress, and output file links. This component will be responsible for managing the polling for a specific job\_id.  
* **Dynamic Step Configuration:** A new type of component that receives an operation name (e.g., ampslice, mfcc) as a prop. It fetches a structured JSON schema from the backend via the /api/v1/operations endpoint and dynamically renders the appropriate UI for each parameter. This ensures the component can handle any new operation without needing a code change. For example, for a threshold parameter with a number type, it would render a number input with a slider.  
* **Step Output Preview:** This is a crucial, smart component designed to render different visualizations based on the type of data returned from a processing step. It will receive an output\_file\_id and the operation type as props. The component will make a request to a new backend endpoint to get the file and its metadata and then render the appropriate UI.  
  * **Audio Files:** For a .wav or .mp3 output, it will render an HTML \<audio\> element with playback controls and an interactive waveform visualization (using a library like **Wavesurfer.js**).  
  * **Spectrograms:** For a spectrogram generated as a .png or .svg, the component will simply display it as an image.  
  * **Matrix Views:** For a structured data output like a CSV or a JSON array (e.g., MFCCs or beat times), the component will render a clean, searchable, and sortable **table view** of the data.  
  * **Scatterplots:** For 2D data like UMAP coordinates, the component will use a visualization library like **D3.js** to render an interactive scatterplot, allowing users to hover over points to see details.  
* **Error Message Component:** A reusable component designed to display structured error messages from the backend. This component will be able to distinguish between an APPLICATION\_ERROR and an INFRASTRUCTURE\_ERROR and show a user-friendly message accordingly.

## **6\. Pipeline Management Endpoints**

The backend's Processing Manager API must be extended to support the persistence of pipeline definitions.

* **POST /api/v1/pipelines**  
  * **Purpose:** To save a new pipeline definition.  
  * **Payload:** A JSON object containing the pipeline array.  
  * **Response:** Returns a pipeline\_id for the newly created definition.  
* **GET /api/v1/pipelines**  
  * **Purpose:** To retrieve all saved pipelines for the current user.  
  * **Response:** Returns a JSON array of pipeline definition documents.  
* **GET /api/v1/pipelines/{pipeline\_id}**  
  * **Purpose:** To retrieve a single pipeline definition by its ID.  
  * **Response:** Returns a single pipeline definition document.  
* **PUT /api/v1/pipelines/{pipeline\_id}**  
  * **Purpose:** To update an existing pipeline definition.  
  * **Payload:** A JSON object with the updated pipeline array.  
* **GET /api/v1/files**  
  * **Purpose:** To retrieve a list of all available audio files for the current user.  
  * **Response:** Returns a JSON array of file metadata documents, including file\_id and a human-readable file\_name.  
* **GET /api/v1/files/{file\_id}**  
  * **Purpose:** To download a specific file. The backend will serve as a proxy, fetching the file from cloud storage and streaming it to the client.  
  * **Response:** The raw file data (e.g., audio, image, CSV).  
* **GET /api/v1/operations**  
  * **Purpose:** To retrieve a structured list of all available operations and their expected parameters.  
  * **Response:** A JSON array of objects, where each object describes an operation and its parameters. The frontend will use this to dynamically build the step configuration UI. For example:

\[  
    {  
        "name": "ampslice",  
        "description": "Slices an audio file into amplitude-based segments.",  
        "parameters": \[  
            {  
                "name": "input",  
                "type": "file\_reference",  
                "description": "The audio file to process."  
            },  
            {  
                "name": "threshold",  
                "type": "number",  
                "description": "The amplitude threshold for slicing.",  
                "min": 0,  
                "max": 1,  
                "default": 0.5  
            }  
        \]  
    },  
    {  
        "name": "mfcc",  
        "description": "Calculates Mel-Frequency Cepstral Coefficients.",  
        "parameters": \[  
            {  
                "name": "input",  
                "type": "file\_reference",  
                "description": "The audio file to process."  
            },  
            {  
                "name": "num\_coefficients",  
                "type": "integer",  
                "description": "The number of coefficients to compute.",  
                "min": 1,  
                "max": 40,  
                "default": 13  
            }  
        \]  
    }  
\]

## **7\. Error Handling and User Feedback**

The frontend will provide immediate and clear feedback to the user when an error occurs.

### **Structured Error Display**

Based on the structured error object from the backend, the frontend will show different messages.

* **APPLICATION\_ERROR:** A user-facing message will explain the issue in simple terms (e.g., "The audio file you provided is corrupt and could not be processed."). The frontend may also offer a "Retry" button for jobs with specific error codes.  
* **INFRASTRUCTURE\_ERROR:** The frontend will display a generic message like, "Something went wrong on our end. Please try again in a few minutes." This prevents users from getting confused by technical details and directs them to a path forward.

### **Key Dependencies**

* React: npm install react react-dom  
* Zustand (or Redux): npm install zustand  
* Tailwind CSS: npm install \-D tailwindcss