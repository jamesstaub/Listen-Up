from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import time


class EventType(str, Enum):
    STATUS_UPDATE = "STATUS_UPDATE"
    FINAL_STATUS = "FINAL_STATUS"
    PROGRESS_UPDATE = "PROGRESS_UPDATE"
    LOG_MESSAGE = "LOG_MESSAGE"
    JOB_SUBMIT = "JOB_SUBMIT"


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
