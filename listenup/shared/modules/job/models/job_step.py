import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from shared.modules.job.models.command_spec import CommandSpec
from pydantic import BaseModel, Field
from shared.modules.job.enums.job_step_state_enum import JobStepState

class JobStep(BaseModel):
    """
    Represents a single step in a Job.
    Shared between backend, microservice, and orchestration layers.
    """
    name: str
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order: Optional[int] = None 
    command_spec: Optional[CommandSpec] = None
    state: JobStepState = JobStepState.PENDING
    inputs: Dict[str, Any] = Field(default_factory=dict)    # Cloud URIs or job outputs
    outputs: Dict[str, Any] = Field(default_factory=dict)   # Output artifacts (URIs or local paths)
    log_tail: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    microservice: Optional[str] = None                      # Which service should run it

    def mark_running(self):
        self.status = JobStepState.RUNNING
        self.started_at = datetime.now()

    def mark_complete(self, outputs: Optional[Dict[str, Any]] = None):
        self.status = JobStepState.COMPLETE
        self.outputs = outputs or {}
        self.finished_at = datetime.now()

    def mark_failed(self, error_message: str):
        self.status = JobStepState.FAILED
        self.error_message = error_message
        self.finished_at = datetime.now()

    def is_complete(self) -> bool:
        return self.status == JobStepState.COMPLETE

    def is_failed(self) -> bool:
        return self.status == JobStepState.FAILED
