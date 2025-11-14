from datetime import time
from shared.modules.job.models.job_step import JobStep
from shared.modules.job.enums.job_step_status_enum import JobStepStatus
from typing import Dict, Any, Optional
from pymongo.collection import Collection

class JobStepModel:
    """
    Backend persistence wrapper for JobStep objects inside MongoDB.
    Steps are stored as part of the parent Job document, but
    this class allows targeted updates for individual steps.
    """

    def __init__(self, collection: Collection):
        self.collection = collection  # mongo.db.jobs

    def update_status(
        self,
        job_id: str,
        step_id: str,
        status: JobStepStatus,
        updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update the status of a single step within a job.
        Uses Mongo's positional array operator to target the right step.
        """
        updates = updates or {}
        update_doc = {"$set": {f"steps.$.{k}": v for k, v in updates.items()}}
        update_doc["$set"]["steps.$.status"] = status

        result = self.collection.update_one(
            {"_id": job_id, "steps.step_id": step_id},
            update_doc
        )
        return result.modified_count > 0

    def append_step(self, job_id: str, step: JobStep):
        """
        Append a new step to a job document.
        """
        result = self.collection.update_one(
            {"_id": job_id},
            {"$push": {"steps": step.dict()}}
        )
        return result.modified_count > 0

    def get_step(self, job_id: str, step_id: str) -> JobStep:
        """
        Retrieve a single step from a job.
        """
        job = self.collection.find_one(
            {"_id": job_id, "steps.step_id": step_id},
            {"steps.$": 1}
        )
        if not job or "steps" not in job or not job["steps"]:
            return None
        return JobStep(**job["steps"][0])