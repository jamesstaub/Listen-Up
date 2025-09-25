# shared/schemas/job_step.py
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from ..enums.job_step_state_enum import JobStepState
import uuid
import time


class JobStep(BaseModel):
    """
    Shared schema for a single step within a Job.
    Used across microservices and backend.
    """
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    order: int
    status: JobStepState = JobStepState.PENDING
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    def mark_running(self):
        self.status = JobStepState.RUNNING
        self.started_at = time.time()

    def mark_complete(self, outputs: Dict[str, Any] = None):
        self.status = JobStepState.COMPLETE
        self.outputs = outputs or {}
        self.finished_at = time.time()

    def mark_failed(self, error_message: str):
        self.status = JobStepState.FAILED
        self.error_message = error_message
        self.finished_at = time.time()

    def is_complete(self) -> bool:
        return self.status == JobStepState.COMPLETE

    def is_failed(self) -> bool:
        return self.status == JobStepState.FAILED
