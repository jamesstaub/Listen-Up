from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
from ..enums.job_status_enum import JobStatus
from .job_step import JobStep

class Job(BaseModel):
    job_id: str
    status: str = JobStatus.PENDING
    steps: List[JobStep] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True  # Store enums as plain strings for Mongo/Redis

    # --- Convenience methods ---
    def is_pending(self) -> bool:
        return self.status == JobStatus.PENDING

    def is_processing(self) -> bool:
        return self.status == JobStatus.PROCESSING

    def is_complete(self) -> bool:
        return self.status == JobStatus.COMPLETE

    def is_failed(self) -> bool:
        return self.status == JobStatus.FAILED

    def get_current_step(self) -> Optional[JobStep]:
        """Return the first non-complete step, or None if all are done."""
        for step in self.steps:
            if not step.is_complete():
                return step
        return None