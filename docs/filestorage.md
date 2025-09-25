# **File Storage and Access Strategy**

This document outlines the architectural plan for managing all file-related data, including user uploads, temporary processing files, and final outputs. The strategy balances performance and security by using a tiered storage approach and managing all permissions at the application level.

## **1\. Core Principles**

* **Single App-Managed Bucket:** All files, regardless of user or storage tier, will reside in a single, primary cloud bucket (e.g., on Amazon S3 or Google Cloud Storage). This is the most secure and manageable approach.  
* **No Direct User Access:** Users and frontend clients will never have direct, long-term credentials for the bucket. All file access will be mediated by the backend application.  
* **Application-Level Permissions:** All access control logic will be enforced by the Django backend, not by complex, per-user IAM rules on the cloud provider.  
* **Performance is Key:** User-provided storage will not be used for real-time processing. Files will be copied to a high-speed, app-managed temporary bucket for all processing tasks.

## **2\. Storage Tiers and Authentication Interaction**

The file storage system will be tightly integrated with the user's authentication and payment tier.

### **a. Free Tier Users (User-Provided Storage)**

* **Authentication:** Users will sign in to the application and use an OAuth flow to connect their personal cloud storage (Google Drive or Dropbox). The application will store a secure, tokenized reference to their external account.  
* **Workflow:**  
  1. User initiates a job on a file in their Google Drive.  
  2. The backend uses the stored token to **copy** the file from the user's cloud storage to a temporary directory in the app's main bucket.  
  3. The microservice processes the file from this temporary location.  
  4. After the job is complete, the backend copies the output files back to a designated folder in the user's personal cloud storage.  
  5. All temporary files are immediately purged from the app's bucket to reduce storage costs and maintain privacy.

### **b. Paid Tier Users (App-Provided Storage)**

* **Authentication:** Paid users will have access to a dedicated, long-term storage space within the application's main bucket. This is tied directly to their user ID and payment status in the SQL database.  
* **Workflow:**  
  1. User uploads a file directly to their provisioned storage space in the app's main bucket.  
  2. The microservice accesses the file directly from this location, eliminating the need for a copy step.  
  3. Output files are saved directly back to the user's provisioned storage. The files persist and are not purged until the user manually deletes them or their subscription ends.

## **3\. Implementing Permissions and Access Control**

### **a. Cloud Bucket Configuration**

The primary bucket will be configured with a strict, "least privilege" security policy. The only entity with full read/write access will be the Django application itself, using a dedicated IAM role or service account credentials.

* **File Path Structure:** All files will be stored with a clear, user-ID-based path.  
  * s3://your-main-bucket/users/\<user\_id\>/\<file\_name.mp3\>  
  * s3://your-main-bucket/temp\_files/\<job\_id\>/\<temp\_file.wav\>  
* **No Per-User Buckets:** This approach avoids the complexity and security risks of managing hundreds or thousands of separate buckets.

### **b. Django Backend as Gatekeeper**

The Django application is the central point of control for all file access. No files are ever accessed by the frontend directly using long-term credentials.

1. **Request Handling:** When a user requests an upload or download URL, the Django view intercepts the request.  
2. **Permission Check:** The view verifies the user's authentication and checks if they have permission to access the requested file path. This is done by comparing the file's path (e.g., s3://.../users/\<user\_id\>/...) to the authenticated user's ID.  
3. **Superadmin Access:** A superuser (request.user.is\_superuser) bypasses the path-based permission check and can generate a signed URL for any file in the bucket.  
4. **Signed URL Generation:** Once authorized, the view generates a **pre-signed URL**. This is a time-limited token that grants temporary permission to perform a single action (GET or PUT) on a specific file. The URL is sent back to the frontend, which can now perform the upload or download securely.

## **4\. Data Integrity and Resiliency with Checksums**

To ensure files are not corrupted during transit, the system will use **checksums** (e.g., a SHA-256 hash). A checksum acts as a unique fingerprint for a file. If even a single bit of the file changes, the checksum will be completely different. This process adds a layer of resilience by allowing both the frontend and backend to verify file integrity.

* **Frontend Check:** Before a file is uploaded, the frontend will calculate its checksum. This hash is then sent along with the job request to the backend.  
* **Backend Verification:** After the file has been uploaded to the app's main bucket, the backend will calculate a new checksum and compare it to the one provided by the frontend. If the checksums don't match, the upload is considered corrupt and the user is notified.  
* **Microservice Verification:** When a microservice receives a job request, it will also receive the file's checksum. It will download the file and verify the checksum **before** beginning any processing. This ensures that the microservice is working on a valid copy of the file.  
* **Output Checksum:** After a microservice has completed its work and saved the output files, it will calculate a new checksum for each of them. This is then included in the final job completion message, allowing the main app to verify the integrity of the output before making it available to the user.

## **5\. Microservice and File Storage Interaction: A Concrete Example**

Here is a step-by-step example of the interaction between the librosa-hpss microservice and the file storage system, with an emphasis on the role of the microservice wrapper.

1. **Job Enqueue:** The Django backend validates a user's request to run an HPSS job. It sends a message to the job queue that includes the file's path in the bucket, the user's ID, and the file's checksum.  
2. **Job Received:** The librosa-hpss microservice wrapper (a Python application) polls the queue and receives the message. It parses the file path and checksum.  
3. **File Download:** The wrapper sends an internal API request to the Django backend asking for a signed URL for the specified file path. The backend generates a temporary, single-use GET URL and returns it. The wrapper then uses this URL to download the file to its local, temporary file system.  
4. **Checksum Verification:** Before doing anything else, the Python wrapper calculates the SHA-256 checksum of the downloaded file and compares it against the checksum received from the queue.  
   \# Conceptual Python code in the microservice wrapper  
   local\_checksum \= calculate\_sha256(local\_file\_path)  
   if local\_checksum \!= job\_data\['checksum'\]:  
       raise ValueError("File checksum mismatch. Corrupted file detected.")

5. **CLI Execution:** The wrapper executes the HPSS binary on the downloaded audio file, which runs the core processing logic.  
   \# Conceptual CLI command  
   subprocess.run(\['librosa-hpss', '--input', local\_file\_path, '--output', temp\_output\_path\])

6. **Output Upload:** After the binary completes, the wrapper calculates the checksum for the harmonic and percussive output files and sends them to the Django backend along with their new file paths. The backend provides signed PUT URLs, and the wrapper uploads the output to the app's bucket.  
7. **Job Completion:** The wrapper sends a final message to a "status" queue, indicating the job's success and including the paths and checksums of the newly created output files. The main app's Django Channels consumer then updates the user's frontend UI.