from enum import Enum

class JobStepStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INITIALIZING = "initializing"
    RUNNING = "running"
    UPLOADING = "uploading"
    COMPLETE = "complete"
    FAILED = "failed"