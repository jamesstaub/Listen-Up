# **Microservice Communication Strategy**

This document outlines the strategy for communication between the main Django application and the backend microservices. The core principle is to use a message queue to **decouple** the services, ensuring the main app remains responsive and resilient to long-running or failing jobs.

## **1\. The Core Workflow**

1. **Job Creation (Frontend to Backend):** The user's browser sends an API request to the main Django application to initiate a job (e.g., "process this audio file").  
2. **Job Validation (Backend):** The Django backend validates the job request against a predefined set of allowed operations and parameters. This is done by checking the request against the service\_manifest.json.  
3. **Queueing (Backend):** If the request is valid, the Django backend creates a job message and pushes it onto a **message queue (Redis)**. The message contains all the necessary information, including the audio file's ID and the specific operation to perform. The use of a message queue is critical for resilience. It allows the backend to handle a high volume of job requests without getting bogged down by a service that is currently busy. If a microservice fails or goes offline, the job message remains in the queue, waiting to be processed when the service comes back online, preventing data loss and ensuring eventual consistency.  
4. **Polling (Microservice):** The target microservice continuously polls the message queue. This polling mechanism is passive, meaning the microservice isn't actively consuming resources unless there's a job to be done. It simply checks the queue at regular intervals, ready to accept work as it becomes available.  
5. **Execution (Microservice):** When a new job message is received, the microservice downloads the necessary audio file from the cloud data store, executes the requested operation, and saves the output back to the cloud. By handling the I/O and computation asynchronously, the microservice can process jobs independently, without blocking other parts of the system.  
6. **Status Update (Microservice to Backend):** The microservice sends a new message to a separate "status" queue, which is consumed by the Django app. This asynchronous update mechanism allows the frontend to provide real-time feedback to the user, showing the status of their job as it progresses from "pending" to "processing" and finally to "complete" or "failed."

## **2\. The Service Manifest (service\_manifest.json)**

To ensure security and a predictable interface, each microservice will have a declarative manifest. This file acts as a single source of truth for all of the microservice's exposed operations. The Django backend uses this file to **validate all incoming job requests** before they are pushed to the queue.

### **Example Manifest**

{  
  "service\_name": "audio-analyzer",  
  "description": "Performs various audio signal analysis operations.",  
  "operations": \[  
    {  
      "name": "librosa-hpss",  
      "description": "Harmonic-Percussive Source Separation using librosa.",  
      "entrypoint\_function": "run\_hpss",  
      "inputs": {  
        "type": "audio",  
        "details": {  
          "channels": 1  
        }  
      },  
      "outputs": {  
        "type": "audio",  
        "details": {  
          "channels": 1,  
          "files": \["harmonic", "percussive"\]  
        }  
      },  
      "parameters": \[  
        {  
          "name": "margin",  
          "type": "float",  
          "default": 1.0,  
          "min": 0.1,  
          "max": 5.0  
        },  
        {  
          "name": "power",  
          "type": "float",  
          "default": 2.0,  
          "min": 1.0,  
          "max": 4.0  
        }  
      \]  
    },  
    {  
      "name": "flucoma-onset",  
      "description": "Onset detection using the Flucoma command-line tool.",  
      "entrypoint\_command": "flucoma-cli-onset",  
      "inputs": {  
        "type": "audio",  
        "details": {  
          "channels": 1  
        }  
      },  
      "outputs": {  
        "type": "matrix",  
        "details": {  
          "columns": 1,  
          "description": "Onset times in seconds"  
        }  
      },  
      "parameters": \[  
        {  
          "name": "threshold",  
          "type": "float",  
          "default": 0.5,  
          "min": 0.0,  
          "max": 1.0  
        }  
      \]  
    },  
    {  
      "name": "librosa-mfcc",  
      "description": "Mel-frequency cepstral coefficients using librosa.",  
      "entrypoint\_function": "run\_mfcc",  
      "inputs": {  
        "type": "audio",  
        "details": {  
          "channels": 1  
        }  
      },  
      "outputs": {  
        "type": "matrix",  
        "details": {  
          "columns": 13,  
          "description": "13 MFCC coefficients"  
        }  
      },  
      "parameters": \[  
        {  
          "name": "n\_mfcc",  
          "type": "integer",  
          "default": 13,  
          "min": 1,  
          "max": 40  
        }  
      \]  
    }  
  \]  
}

## **3\. The Shared Validation Module**

To prevent malicious or malformed requests from ever reaching the core processing logic, each microservice will use a shared validation module. This module will be housed in a shared/ directory in the monorepo and imported by all microservices. It performs a final, critical set of checks before a job is executed.

### **Responsibilities:**

* **Validate Job Parameters:** Checks the job message against the service\_manifest.json to ensure all parameters are of the correct type and within the specified range.  
* **Validate Input Assets:** Before processing begins, it performs pre-execution checks on the input file itself. This is a crucial step to prevent errors from bad files. For audio files, this might involve:  
  * **Existence Check:** Verify that the file exists in cloud storage.  
  * **Format Check:** Use FFprobe to ensure the file is a valid audio format (e.g., MP3, WAV, FLAC).  
  * **File Integrity & Content Check:** Use a **checksum** of the file's content to ensure it has not been corrupted or changed. This is especially important for jobs with a file path as an input, as the file content can change without the path changing.  
  * **Data Shape Check:** Verify that the audio file's channel count matches the channels specified in the manifest.

## **4\. The Microservice Wrapper**

Each microservice will have a simple Python application—a wrapper—that handles all communication. Its job is to act as the middleman between the message queue, the cloud data store, and the core processing logic.

### **Responsibilities:**

* **Consume Queue Events:** Listen for new jobs from the message queue.  
* **Access Data Store:** Use an official client library (e.g., boto3 for AWS S3) to download input files and upload output files. All access is handled via pre-signed URLs or dedicated IAM roles.  
* **Execute Core Logic:** Run the necessary librosa, flucoma, or other code based on the job message.  
* **Update Status:** Send status messages back to the Django app via a dedicated status queue.

### **Example Workflow (Conceptual Code):**

import redis  
import json  
import boto3  
import os  
from shared.python.utils import get\_file\_from\_storage, upload\_file\_to\_storage  
from shared.python.validation import validate\_job\_message

\# This is a conceptual example, actual implementation will be more robust.

\# Redis client  
redis\_client \= redis.Redis(host='redis', port=6379, db=0)

\# S3 client  
s3\_client \= boto3.client('s3')

\# Main loop that listens for jobs  
def listen\_for\_jobs():  
    while True:  
        \# Blocking call to wait for a message  
        job\_message \= redis\_client.brpop('audio\_jobs\_queue')\[1\]  
        job\_data \= json.loads(job\_message)

        try:  
            \# 1\. Validate the job using the shared module  
            validated\_job\_data \= validate\_job\_message(job\_data)

            \# 2\. Access the data store using the validated data  
            file\_path \= get\_file\_from\_storage(validated\_job\_data\['file\_id'\])

            \# 3\. Execute the core logic  
            if validated\_job\_data\['operation'\] \== 'librosa-hpss':  
                \# Example: Calls a pre-baked function  
                harmonic, percussive \= run\_hpss\_analysis(file\_path, \*\*validated\_job\_data\['parameters'\])  
                \# Upload output files to storage  
                upload\_file\_to\_storage(harmonic, f"harmonic\_{validated\_job\_data\['file\_id'\]}")  
                upload\_file\_to\_storage(percussive, f"percussive\_{validated\_job\_data\['file\_id'\]}")

            elif validated\_job\_data\['operation'\] \== 'flucoma-onset':  
                \# Example: Executes a CLI command  
                subprocess.run(\['flucoma-cli', 'onset', file\_path, f"output\_{validated\_job\_data\['file\_id'\]}"\])

            \# 4\. Update the status  
            redis\_client.lpush('status\_queue', json.dumps({'job\_id': validated\_job\_data\['job\_id'\], 'status': 'complete'}))

        except Exception as e:  
            \# Handle failure  
            print(f"Job failed: {e}")  
            redis\_client.lpush('status\_queue', json.dumps({'job\_id': job\_data\['job\_id'\], 'status': 'failed', 'error': str(e)}))

\# Other helper functions  
def run\_hpss\_analysis(file\_path, margin, power):  
    import librosa  
    y, sr \= librosa.load(file\_path)  
    \# Perform HPSS using the provided parameters  
    return librosa.effects.hpss(y, margin=margin, power=power)

if \_\_name\_\_ \== "\_\_main\_\_":  
    listen\_for\_jobs()

## **5\. The Multi-Microservice Pipeline**

For complex workflows that require multiple, distinct operations, the backend will act as an orchestrator. Instead of a single job per operation, the frontend can request a **pipeline** that the backend manages. This allows for a single user action to trigger a chain of events across different microservices.

### **Workflow:**

1. **Frontend Request:** The frontend sends a single request to the backend with a high-level job ID and a list of steps, each with its parameters.  
2. **Backend Validation:** The backend is responsible for validating the entire pipeline. It iterates through the requested steps and, for each step, looks up the corresponding manifest for the correct microservice. It validates the parameters and ensures that the output of one step will match the expected input of the next.  
3. **Orchestration:** Once the pipeline is validated, the backend pushes a job to the queue for only the first microservice. When that microservice completes its task, it sends a status update to the backend. The backend's orchestration logic sees this completion and then queues the next step to the appropriate microservice. This continues until the entire pipeline is complete.

### **Example Pipeline in a Job Message:**

{  
  "job\_id": "abcde123...",  
  "file\_id": "audio-file-123",  
  "pipeline": \[  
    {  
      "step\_id": 1,  
      "service": "flucoma-service",  
      "operation": "bufcompose",  
      "parameters": {  
        "channels": 2  
      }  
    },  
    {  
      "step\_id": 2,  
      "service": "flucoma-service",  
      "operation": "ampslice",  
      "parameters": {}  
    },  
    {  
      "step\_id": 3,  
      "service": "librosa-service",  
      "operation": "librosa-mfcc",  
      "parameters": {  
        "n\_mfcc": 40  
      }  
    },  
    {  
      "step\_id": 4,  
      "service": "flucoma-service",  
      "operation": "robustscaling",  
      "parameters": {}  
    }  
  \]  
}

This approach allows you to build sophisticated, multi-step workflows while keeping your microservices simple and single-purpose. The backend handles the complexity of sequencing and validation, providing a robust and secure API for the frontend.

## **6\. Caching Deterministic Results**

To avoid redundant computation and improve the responsiveness of the pipeline, we will implement a caching strategy for all deterministic operations. A **deterministic** operation is one that will always produce the exact same output given the same input parameters.

### **Caching Strategy**

1. **Cache Key Generation:** Before a microservice begins processing a task, it will generate a unique cache key. This key will be a hash of the operation's name and the input parameters, along with a **checksum of the input file's content**. This ensures the key is unique to a specific operation and a specific version of the input file, preventing a change in the file from being missed by the cache.  
2. **Manifest Configuration:** The service\_manifest.json will be extended to include two new fields for each operation:  
   * cachable: A boolean that indicates whether the operation is deterministic and its output can be cached.  
   * cache\_duration\_minutes: An integer that defines how long the cached output is valid.  
3. **NoSQL Datastore as the Cache:** The microservice will use a dedicated collection in a **NoSQL datastore (like Firestore or MongoDB)** to store cache hits. The document ID will be the generated cache key, and the document will contain a timestamp and the output file ID.

### **The Caching Workflow**

1. **Check Cache:** When a microservice receives a job, it first generates the unique cache key. It then performs a quick lookup in the datastore's cache collection.  
2. **Cache Hit:** If a document with a matching key is found and its timestamp is still valid (i.e., less than cache\_duration\_minutes old), the microservice will **skip the computation**. Instead, it will simply update the datastore's job document with the cached output file ID, mark the step as completed, and send the status update to the backend. This saves significant time and resources.  
3. **Cache Miss:** If no matching key is found or the cache has expired, the microservice proceeds with the computation as normal.  
4. **Populate Cache:** After a successful computation, and if the operation is marked as cachable in the manifest, the microservice will create or update the cache document in the datastore with the newly generated output file ID and the current timestamp.

This strategy ensures that any previously computed result is reused, benefiting both the user with faster response times and the system by reducing unnecessary load.

## **7\. Detailed Pipeline Orchestration**

The backend's role as the central orchestrator is critical for handling multi-step pipelines. Instead of a single, fire-and-forget job message, the backend maintains the state of the entire pipeline in the **NoSQL datastore** and manages the flow between services.

### **The Datastore Document as the Source of Truth**

The backend will create a single **document** in the datastore for each pipeline job. This document will serve as the master record, providing real-time status updates for the frontend.

**Example Datastore Document:**

full_job_data = {
    "job_id": "job_12345",
    "state": "pending",
    "current_step_index": 0,
    "steps": [
        {
            "name": "ampslice",
            "step_type": "flucoma",
            "command_template": (
                "fluid-ampslice "
                "{source} {indices} "
                "-onthreshold {onthreshold} "
                "-offthreshold {offthreshold} "
                "-slowrampup {slowrampup} "
                "-slowrampdown {slowrampdown} "
                "-fastrampup {fastrampup} "
                "-fastrampdown {fastrampdown} "
                "-floor {floor} "
                "-highpassfreq {highpassfreq} "
                "-minslicelength {minslicelength} "
                "-numchans {numchans} "
                "-numframes {numframes} "
                "-startchan {startchan} "
                "-startframe {startframe} "
                "-warnings {warnings}"
            ),
            "inputs": {
                "source": "s3://bucket/audio/input.wav",
                "onthreshold": 0.5,
                "offthreshold": -20.0,
                "slowrampup": 100,
                "slowrampdown": 100,
                "fastrampup": 1,
                "fastrampdown": 1,
                "floor": -144.0,
                "highpassfreq": 85.0,
                "minslicelength": 2,
                "numchans": -1,
                "numframes": -1,
                "startchan": 0,
                "startframe": 0,
                "warnings": 1
            },
            "outputs": {
                "indices": "output_indices.json"
            }
        }
    ]
}

### **The Orchestration Flow: Parallel and Serial Execution**

The pipeline orchestration supports both sequential (serial) and simultaneous (parallel) execution of steps. This allows for significant performance gains when processing large amounts of data. The backend manages this by using a "fan-out/fan-in" pattern.

**Fan-out (Parallel Execution):** This occurs when a single task can be broken down into many smaller, independent sub-tasks. The backend's Processing Manager will create and queue a job message for each sub-task simultaneously. Multiple microservice instances can then pick up and process these jobs in parallel. For example, slicing a large audio file into 10-second chunks and then queuing an individual "analyze" job for each chunk.

Fan-Out with Redis
The fan-out part is straightforward. You'll use Redis as a standard message queue.

The "Slicer" Service: When your initial service (the one that slices the audio file) completes its task, it won't queue a single message. Instead, it will queue a message for each audio slice it creates. All these messages go into the same Redis queue.

The "Analyzer" Microservices: Your fleet of parallel analyzer microservices will all be workers constantly listening to this single queue. They'll use the blocking BLPOP command, which allows them to wait efficiently for a new message to arrive. When a message is pushed to the list, Redis ensures that only one of the waiting workers receives it, effectively distributing the workload.


**Fan-in (Serial Execution):** This is a waiting step that requires all the parallel sub-tasks to be completed before it can begin. A final, serial step might aggregate the results from all the processed chunks (e.g., calculating the average loudness across the entire file) or run a final analysis on the combined data. The backend will not queue this final job until it has received status updates for all of the parallel jobs.

Fan-In with Redis
The fan-in part is the more complex challenge. The final service (the one that runs statistics) needs to know that all the parallel analysis jobs are complete before it can begin. You can achieve this using a simple, but powerful, mechanism in Redis: an atomic counter.

The Master Counter: When the "Slicer" service creates the N sub-tasks, it also creates a unique key in Redis, such as job:{id}:tasks_remaining. It then uses the SET command to initialize this key's value to N.

The Decrementing: As each parallel "Analyzer" microservice completes its task, it will perform two actions:

It will write its output to cloud storage.

It will send a message back to the backend. Crucially, it will also send a message to Redis to atomically decrement the counter using the DECRBY command. This ensures the counter is always accurate, even if many workers are finishing at the same time.

The Final Task: The backend Processing Manager will not queue the final "statistics" job until it sees that the counter for that specific job has reached zero. This can be done by a simple check of the key's value after a message is received from a worker. When INCRBY returns a value of 0, the backend knows all parallel tasks are finished and can then queue the final job.

This pattern, using different Redis data structures for different phases of the pipeline, is a very common way to handle complex orchestration without relying on a dedicated message broker.

### **The Orchestration Flow**

1. **Initial Request:** The backend receives a request from the frontend with a pipeline defined.  
2. **Datastore Initialization:** The backend creates the new datastore document for the job, with all steps set to pending and an overall status of in\_progress. The document will also store a count of the parallel jobs created and a reference to the next serial step.  
3. **Step 1 Queueing:** The backend looks at the first step in the pipeline.  
   * **Serial:** It queues a single job message to the appropriate service.  
   * **Parallel:** It breaks the task into multiple sub-tasks (e.g., by chunking a large file) and queues a job message for each sub-task to the appropriate service.  
4. **Microservice Execution:** The microservice picks up the message, performs the operation, and saves the output to the cloud.  
5. **Microservice Chaining and Datastore Update:** **Crucially**, after completing its assigned step, the microservice will check the datastore document to see if the **next step** in the pipeline is a local operation that it can perform.  
   * If the service name and operation for the next step match its own capabilities, it will initiate that next step directly within the same instance, then update the datastore document for both the just-completed step and the newly initiated one.  
   * If the next step requires a different service, the microservice simply updates the datastore document for the completed step and sends a status update message to the backend orchestrator, which will then queue the next job for the appropriate service.  
6. **Next Step Orchestration:** The backend's orchestration logic is notified of the completed step.  
   * **Serial:** It queues the next job, using the **output\_file\_id from the previous step** as the new input\_file\_id.  
   * **Parallel (Fan-in):** It updates the completion count for the parallel step. When the count reaches the total number of sub-tasks, it queues the next serial job.  
7. **Completion:** The process repeats until all steps are marked as completed. The backend then sets the overall job status to complete. In the event of a failure at any step, the microservice will update the status to failed, which the orchestrator will catch, preventing subsequent steps from being queued.

This model ensures a secure, resilient, and transparent pipeline. The frontend can simply listen to the datastore document to provide the user with real-time status updates for each step of their complex job.

## **8\. The Backend Processing Manager**

The backend's Processing Manager is the central hub for all job orchestration. It acts as an API gateway, a validation layer, and a task router. Its role is to take a single user request and break it down into the correct, sequenced messages for the microservice queue.

### **Core Responsibilities**

* **API Endpoint:** Exposes a simple, RESTful API for the frontend to create and track jobs.  
* **Request Validation:** Uses the service\_manifest.json to ensure every incoming request is valid and secure.  
* **Job Initialization:** Creates and populates the master job document in the **NoSQL datastore** to serve as the single source of truth for the entire pipeline.  
* **Task Queueing:** Pushes messages to the Redis queue, which the microservices are listening for.  
* **Status Monitoring:** Consumes messages from the status queue to update the datastore job document in real-time.

### **Proposed API**

The API will be simple and minimal, providing only what's necessary to interact with the job system. All endpoints are protected by authentication, and the user's ID is used to scope job access.

* **POST /api/v1/jobs**  
  * **Purpose:** To create a new job or a multi-step pipeline.  
  * **Payload:** A JSON object containing the input\_file\_id and the pipeline array, as shown in the example in Section 5\.  
  * **Response:** Returns a JSON object with the unique job\_id and a status of pending. The frontend can then use this job\_id to poll for updates.  
* **GET /api/v1/jobs/{job\_id}**  
  * **Purpose:** To retrieve the current status of a specific job.  
  * **Response:** Returns the full job document from the datastore, including the overall status and the status of each step in the pipeline. This provides the frontend with a complete, real-time view of the job's progress.

### **Common Python Modules**

The Processing Manager's logic will be built directly into the Django framework. While we'll still use common, cloud-agnostic Python libraries, we can rely on Django's built-in capabilities for a lot of the heavy lifting.

* **Django**: We'll use Django to build the RESTful API endpoints, manage models, and handle authentication.  
* **redis-py**: The official Python client for Redis, used to interact with the message queues. This is the key to decoupling the backend from the microservices.  
* **hashlib**: For generating cryptographic hashes to create the checksums for caching and file integrity checks.  
* **NoSQL SDK**: We can use either the **Firebase SDK** or a Python driver for MongoDB like **PyMongo** to interact with the chosen datastore.

The Processing Manager's design, using these standard modules and a clear API, keeps it robust, scalable, and portable across different cloud environments.

### **9\. Error Handling and Retries**

A production-ready system must be resilient to failures. Our approach will be to fail gracefully and to provide a clear path for retrying or handling a failed job. To provide actionable information, we will introduce a structured error object.

* **Structured Error Object**: When a microservice encounters an error, it will create a standardized JSON object to be stored in the datastore and sent to the backend. This allows for automated error handling and clearer messaging.  
  **Example error object:**  
  {  
    "error\_type": "APPLICATION\_ERROR",  
    "error\_code": "INVALID\_INPUT\_FILE",  
    "error\_message": "librosa.load() failed: 'file.mp3' is not a valid MP3 file.",  
    "raw\_traceback": "Traceback (most recent call last):\\n  File \\"/app/main.py\\", line 42, in process\_job\\n    ...\\n"  
  }

* **Microservice Level**: A microservice will differentiate between errors using try/except blocks.  
  * **APPLICATION\_ERROR**: Catches errors from the core logic (e.g., a ValueError from a library, an invalid parameter in the job message, or a bad input file). The microservice sets the job status to failed with the new error object.  
  * **INFRASTRUCTURE\_ERROR**: Catches errors related to external dependencies (e.g., redis.exceptions.ConnectionError, a cloud storage timeout). The microservice sets the job status to failed with the new error object.  
* **Backend Level**: The backend's Processing Manager will monitor for failed jobs. It will:  
  * Expose a POST /api/v1/jobs/{job\_id}/retry endpoint. This allows the frontend to explicitly re-queue a failed job.  
  * The retry mechanism will simply create a new job message with the same payload and push it back onto the queue, giving the user control over when to try again. The error\_type will determine whether an automatic retry is appropriate or if it requires manual intervention.

### **10\. Monitoring and Observability**

To understand system health and troubleshoot issues, we need to add logging, metrics, and alerting.

* **Structured Logging**: All components (Django backend, microservices, and wrappers) will emit structured logs in a common format (e.g., JSON). Logs will include key information like job\_id, step\_id, service\_name, timestamp, and log\_level. This allows for easy parsing and searching using a log aggregation service.  
* **Application Metrics**: We will collect metrics on job processing, such as:  
  * **Queue length**: How many jobs are pending?  
  * **Processing time**: How long does each step or pipeline take?  
  * **Success/failure rate**: What percentage of jobs are completed successfully?  
* **Alerting**: Alerts will be configured to notify us of critical events, such as a microservice experiencing a high failure rate, the Redis queue growing too large, or a job taking an unusually long time to complete.

[Image of a warning sign](https://encrypted-tbn2.gstatic.com/licensed-image?q=tbn:ANd9GcSfczkh8FZQyo1SdgOXD_Uju3WrhQvk2-NBbJdRG7_eSd4sizlV3RQWkTrXi67JVYDFVKMIQdIhKVS92RJ9ngkjqlmkmIfi6imdzfr7eXWSHSbo5DE)

### **11\. Versioning and Lifecycle Management**

To manage the lifecycle of our APIs and microservices, we will implement a versioning strategy.

* **API Versioning**: The backend API will be versioned using the URL (e.g., /api/v1/jobs). This ensures that changes to the API don't break older clients.  
* **Manifest Versioning**: The service\_manifest.json will be versioned. The microservice wrapper will be able to handle multiple versions of the manifest, allowing for a phased rollout of new features.

### **12\. Key Infrastructure Components**

While the design is cloud-agnostic, implementing it will require several key components.

* **Stateless Containers**: The Django backend and all microservices will be deployed as stateless, containerized applications. This makes them easy to scale horizontally.  
* **Redis Instance**: A managed Redis service will be used for the message queues.  
* **NoSQL Datastore**: A managed NoSQL database service (like Firestore or MongoDB Atlas) will be used for state management.  
* **Object Storage**: A cloud object storage service (like Google Cloud Storage) will be used to store input and output files.


# Event-Driven Architecture: "Fat" vs. "Thin" Events

In a microservices-based system, the way information is passed between services via a message queue is a critical architectural decision. This document details the key tradeoffs between two primary approaches: sending "thin" events with minimal data or "fat" events with a full payload.

---

## The "Thin" Event Architecture

In this model, the message in the job queue is a lightweight pointer, containing only a unique identifier, such as a **Job ID**. The receiving microservice is responsible for using this ID to query a central database to retrieve all the necessary information, parameters, and state for the job.



### Pros:

* **Single Source of Truth:** The database is the authoritative source for all job-related data. This eliminates the risk of data getting out of sync.
* **Flexibility & Decoupling:** The microservices are not tightly coupled to the message format. If you need to add a new parameter to a job, you just update the database schema; you do not need to redeploy all of your services.
* **Ease of Resubmission:** If a job fails, you can simply re-queue the Job ID. The microservice will always pull the latest, most accurate data from the database.

### Cons:

* **Increased Latency:** Every time a microservice picks up a job, it must make an additional network call to the database. This adds a small but measurable amount of latency to each job's processing time.
* **Higher Database Load:** A high volume of jobs could lead to a significant number of read operations on the database, which may become a performance bottleneck if not managed correctly.

---

## The "Fat" Event Architecture

In this model, the message event contains a complete, self-contained JSON payload with all the data needed for a microservice to execute its task. The microservice can begin processing immediately without querying the database for parameters.



### Pros:

* **Low Latency:** The microservice has all the information it needs immediately. This is ideal for time-critical tasks with extremely high throughput requirements, as it eliminates the extra database query.
* **Reduced Database Load:** The database is only used for the initial creation and final completion of a job, not during every processing step.
* **Stateless Services:** The microservices are completely stateless and "dumb." They just process the data they are given.

### Cons:

* **Data Inconsistency:** This is the most significant drawback. If a job's parameters are updated in the database after the "fat" event has been queued, the microservice will process the job using outdated information, leading to incorrect results.
* **Rigid Architecture:** Any change to the event payload requires a coordinated update and redeployment of all services that interact with that event. This makes the system less flexible.

---

## Final Recommendation

Based on the project's requirements for a complex, scalable, and resilient system, we will proceed with the **"thin" event architecture**.

The key driver for this decision is the need for a **single source of truth** for our pipeline data. The potential for data inconsistency with the "fat" event model poses a far greater long-term risk than the manageable performance concerns of the "thin" model.

By using thin events, our system gains:

* **Data Integrity:** The Firestore database will be the definitive source for all job parameters and status, ensuring that all services are always working with the correct information.
* **Simplified Error Handling:** It will be easy to debug and re-run failed jobs by simply re-queuing the Job ID.
* **Flexibility:** As we add more complex steps and parameters to our pipelines, the system will remain flexible, as we only need to update the database schema, not the message contract between services.

The potential for increased database load can be effectively mitigated through best practices such as **connection pooling** and **batched writes**, which Firestore fully supports. This allows us to leverage the benefits of a robust data model without sacrificing performance.

This document is a great reference for our project. Let me know if you would like to make any changes to it or if you have any other questions about the architecture.


The microservice doesn't have the database credentials to directly query the job collection in MongoDB. Giving every microservice direct database access would be a massive security and maintenance risk.

The solution, which we touched on briefly, is that the microservice uses a dedicated internal API on the main backend to get its instructions. The job ID is the key that it uses to unlock the rest of the information.

Here is the step-by-step flow, referencing our project's architecture documents:

**The Internal API Handshake**
Event in the Queue: The Processing Manager (which is part of our main_app as described in monorepo_architecture_updated.md) sends a thin event to the message queue containing only the job_id.

Microservice Receives Event: A dedicated microservice, such as audio_analyzer or umap_service, picks up the message from the queue. It now knows what job to do, but it doesn't yet know what to do with it.

Internal API Call: The microservice immediately makes a secure API call to the main backend's internal endpoint. For example, it would call an endpoint like GET /api/internal/jobs/<job_id>. As detailed in our monorepo_architecture_updated.md file, this communication would use the helper functions from the shared/api-clients directory.

Backend Queries the Database: The main backend is the sole service with direct credentials to the database. It receives the API call, uses the job_id to look up the complete job parameters from the pipelines collection, and returns a JSON response with all the WorkflowParameters, file paths, and other necessary data.

Microservice Executes: The microservice now has all the instructions it needs. It is still a stateless, "dumb" service because it never had to know about the database. It simply processes the data it was given by a trusted internal source.

This design is exactly the same as our strategy for handling file access. The microservice doesn't have cloud storage credentials; it makes an API call to the backend, which then returns a pre-signed URL to a file.  We are applying the same secure and controlled pattern to our database access.

This ensures the main_app remains the central authority and gatekeeper for all data, while keeping our specialized microservices simple, secure, and highly scalable.