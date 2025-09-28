from enum import Enum
from typing import Any, Dict, Optional, List
from shared.modules.job.enums.job_step_state_enum import JobStepState
from pydantic import BaseModel, Field
from datetime import datetime
import time


class EventType(str, Enum):
    STATUS_UPDATE = "STATUS_UPDATE"
    FINAL_STATUS = "FINAL_STATUS"
    PROGRESS_UPDATE = "PROGRESS_UPDATE"
    LOG_MESSAGE = "LOG_MESSAGE"
    JOB_SUBMIT = "JOB_SUBMIT"
    JOB_STEP_EXECUTE = "JOB_STEP_EXECUTE"
    JOB_STEP_COMPLETE = "JOB_STEP_COMPLETE"
    JOB_STEP_FAILED = "JOB_STEP_FAILED"


class JobEvent(BaseModel):
    """Schema for all job-related queue events."""

    job_id: str = Field(..., description="Unique ID of the job this event belongs to")
    type: EventType = Field(..., description="Type of the event")
    status: Optional[str] = Field(
        None, description="Job status (pending, processing, complete, failed)."
    )
    message: Optional[str] = Field(
        None, description="Message for progress/log events"
    )
    level: Optional[str] = Field(
        None, description="Log level for LOG_MESSAGE (e.g. INFO, WARN, ERROR)"
    )
    percentage: Optional[float] = Field(
        None, description="Completion percentage for PROGRESS_UPDATE"
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary structured payload"
    )
    timestamp: float = Field(
        default_factory=lambda: time.time(), description="Event creation time (epoch)"
    )

    class Config:
        use_enum_values = True


class JobStepEvent(BaseModel):
    """Event sent TO microservices to execute a single step"""
    event_type: str = "JOB_STEP_EXECUTE"
    job_id: str
    step_id: str
    step_name: str
    service: str
    operation: str
    command: str = Field(..., description="Complete command template to execute")
    expected_outputs: List[str] = Field(default_factory=list, description="Expected output file paths")
    inputs: List[str] = Field(default_factory=list)  # List of absolute URIs for input files
    
    # File mapping information for the microservice
    input_file_mapping: Dict[str, str] = Field(default_factory=dict, description="Maps command placeholders to input URIs")
    output_file_mapping: Dict[str, str] = Field(default_factory=dict, description="Maps command placeholders to expected output paths")
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Keep parameters for backward compatibility/logging, but command is primary
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Original parameters for reference")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }



class JobStepStatusEvent(BaseModel):
    """Event sent FROM microservices after step completion"""
    event_type: str  # JOB_STEP_COMPLETE, JOB_STEP_FAILED
    job_id: str
    step_id: str
    step_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: JobStepState
    outputs: List[str] = Field(default_factory=list)  # List of absolute URIs
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
