from __future__ import annotations
from typing import Optional, List
from datetime import datetime
import uuid
from pydantic import BaseModel, Field
from enum import Enum
from ..enums.job_status_enum import JobStatus
from .job_step import JobStep
from .step_transition import StepTransition

class Job(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # User context for storage management
    user_id: Optional[str] = None
    
    status: str = JobStatus.PENDING
    steps: List[JobStep] = Field(default_factory=list)
    step_transitions: List[StepTransition] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True  # Store enums as plain strings for Mongo/Redis
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    # --- Convenience methods ---
    def is_pending(self) -> bool:
        return self.status == JobStatus.PENDING

    def is_processing(self) -> bool:
        return self.status == JobStatus.PROCESSING

    def is_complete(self) -> bool:
        return self.status == JobStatus.COMPLETE

    def is_failed(self) -> bool:
        return self.status == JobStatus.FAILED
