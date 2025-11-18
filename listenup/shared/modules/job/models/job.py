from __future__ import annotations
from typing import Optional, List, Dict, Any
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
    
    status: JobStatus = JobStatus.PENDING
    steps: List[JobStep] = Field(default_factory=list)
    step_transitions: List[StepTransition] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True  # Store enums as plain strings for Mongo/Redis
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    
    def get_step_outputs(self, step_id: str) -> Dict[str, Any]:
        """
        Get outputs from a specific step in this job.
        Returns empty dict if step not found or has no outputs.
        """
        step = self.find_step(step_id)
        if not step:
            return {}
        
        return step.outputs
    
    def find_step(self, step_id: str) -> Optional['JobStep']:
        """
        Find a step by ID with proper typing.
        Returns None if not found.
        """
        return next((s for s in self.steps if s.step_id == step_id), None)
