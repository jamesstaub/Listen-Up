from datetime import datetime
from shared.modules.job.models.job_step import JobStep
from shared.modules.job.enums.job_step_status_enum import JobStepStatus
from typing import Dict, Any, Optional
from pymongo.collection import Collection
from backend.models.base_nosql_model import BaseNoSqlModel

class JobStepModel(BaseNoSqlModel):
    """
    Backend persistence wrapper for JobStep objects inside MongoDB.
    Steps are stored as part of the parent Job document, but
    this class allows targeted updates for individual steps.
    """

    @property
    def collection(self) -> Collection:
        """Get the jobs collection from the database."""
        return self.db.jobs

    @classmethod
    def update_step_status(
        cls,
        job_id: str,
        step_id: str,
        status: JobStepStatus,
        outputs: Optional[Dict[str, Any]] = None,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update a step's status and related fields within a job.
        Uses MongoDB's positional array operator to target the right step.
        """
        from datetime import datetime
        
        instance = cls()
        update_fields = {
            "steps.$.status": status.value,
            "updated_at": datetime.utcnow()
        }
        
        if outputs is not None:
            update_fields["steps.$.outputs"] = outputs
        if started_at is not None:
            update_fields["steps.$.started_at"] = started_at
        if finished_at is not None:
            update_fields["steps.$.finished_at"] = finished_at
        if error_message is not None:
            update_fields["steps.$.error_message"] = error_message

        result = instance.collection.update_one(
            {"_id": job_id, "steps.step_id": step_id},
            {"$set": update_fields}
        )
        return result.modified_count > 0

    @classmethod
    def append_step(cls, job_id: str, step: JobStep) -> bool:
        """
        Append a new step to a job document.
        """
        instance = cls()
        result = instance.collection.update_one(
            {"_id": job_id},
            {"$push": {"steps": step.dict()}}
        )
        return result.modified_count > 0

    @classmethod
    def get_step(cls, job_id: str, step_id: str) -> Optional[JobStep]:
        """
        Retrieve a single step from a job.
        """
        instance = cls()
        job = instance.collection.find_one(
            {"_id": job_id, "steps.step_id": step_id},
            {"steps.$": 1}
        )
        if not job or "steps" not in job or not job["steps"]:
            return None
        return JobStep(**job["steps"][0])