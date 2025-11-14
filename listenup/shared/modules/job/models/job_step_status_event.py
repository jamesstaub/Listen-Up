from enum import Enum
from typing import Any, Dict, Optional, List
from shared.modules.job.enums.job_step_state_enum import JobStepState
from pydantic import BaseModel, Field
from datetime import datetime

class JobStepStatusEvent(BaseModel):
    """Event sent FROM microservices after step completion"""
    event_type: str  # JOB_STEP_COMPLETE, JOB_STEP_FAILED
    job_id: str
    step_id: str
    step_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: JobStepState
    outputs: Optional[Dict[str, Any]] = Field(default_factory=dict)  # Dict mapping output names to URIs
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
