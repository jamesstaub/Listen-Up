from enum import Enum

class JobStepState(str, Enum):
    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    UPLOADING = "uploading"
    COMPLETE = "complete"
    FAILED = "failed"