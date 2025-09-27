from typing import Any, Dict, Optional
from shared.modules.job.events import JobEvent, EventType
from .models.job import Job
from .models.job_step import JobStep


class JobEventFactory:
    """Factory for building JobEvent objects from Jobs or JobSteps."""

    @staticmethod
    def _serialize_job_for_payload(job: "Job") -> Dict[str, Any]:
        """Manually serialize job to handle datetime objects."""
        job_dict = job.dict(exclude_none=True)
        # Convert datetime objects to ISO strings
        if job_dict.get('created_at'):
            job_dict['created_at'] = job.created_at.isoformat()
        if job_dict.get('updated_at'):
            job_dict['updated_at'] = job.updated_at.isoformat()
        return job_dict

    @staticmethod
    def from_new_job(job: "Job") -> JobEvent:
        return JobEvent(
            job_id=job.job_id,
            type=EventType.JOB_SUBMIT,
            status=job.status,
            payload={
                "job": JobEventFactory._serialize_job_for_payload(job),
                "steps": [step.dict(exclude_none=True) for step in job.steps],
                "created_at": job.created_at.isoformat() if job.created_at else None,
            },
        )
    
    @staticmethod
    def from_job_status(job: "Job", status: Optional[str] = None) -> JobEvent:
        return JobEvent(
            job_id=job.job_id,
            type=EventType.STATUS_UPDATE,
            status=status or job.status,
            payload={
                "current_step_index": job.current_step_index,
                "total_steps": len(job.steps),
            },
        )

    @staticmethod
    def from_job_final(job: "Job", payload: Optional[Dict[str, Any]] = None) -> JobEvent:
        return JobEvent(
            job_id=job.job_id,
            type=EventType.FINAL_STATUS,
            status=job.status,
            payload=payload or {"steps": [step.dict() for step in job.steps]},
        )

    @staticmethod
    def from_step_update(job: "Job", step: "JobStep") -> JobEvent:
        return JobEvent(
            job_id=job.job_id,
            type=EventType.STATUS_UPDATE,
            status=job.status,
            payload={
                "current_step": step.name,
                "step_index": job.current_step_index,
                "step_state": step.state,
                "step_outputs": step.outputs,
            },
        )

    @staticmethod
    def from_progress(job_id: str, message: str, percentage: Optional[float] = None) -> JobEvent:
        return JobEvent(
            job_id=job_id,
            type=EventType.PROGRESS_UPDATE,
            message=message,
            percentage=percentage,
        )

    @staticmethod
    def from_log(job_id: str, message: str, level: str = "INFO") -> JobEvent:
        return JobEvent(
            job_id=job_id,
            type=EventType.LOG_MESSAGE,
            message=message,
            level=level,
        )