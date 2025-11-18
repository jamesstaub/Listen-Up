from datetime import datetime
from typing import List, Dict, Optional, Any

from pymongo.collection import Collection
from shared.modules.job.models.job import Job
from shared.modules.job.models.job_step import JobStep
from shared.modules.job.enums.job_status_enum import JobStatus
from shared.modules.job.enums.job_step_status_enum import JobStepStatus
from backend.models.base_nosql_model import BaseNoSqlModel


class JobModel(BaseNoSqlModel):
    """
    MongoDB persistence wrapper for Job objects.
    Inherits common CRUD operations from BaseNoSqlModel.
    """

    @property
    def collection(self) -> Collection:
        """Get the jobs collection from the database."""
        return self.db.jobs

    @classmethod
    def _from_doc(cls, doc: Dict[str, Any]) -> Job:
        """
        Convert MongoDB document to Job instance.
        """
        doc["job_id"] = str(doc["_id"])
        del doc["_id"]  # Remove MongoDB's _id field
        return Job(**doc)

    @classmethod
    def get_step_outputs(cls, job_id: str, step_id: str) -> Dict[str, Any]:
        """
        Retrieve the outputs of a specific step in a job as a dictionary.
        Delegates to the Job domain object's instance method.
        """
        job = cls.find(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        return job.get_step_outputs(step_id)

    @classmethod
    def update_job_step_status(
        cls,
        job_id: str,
        step_id: str,
        status: JobStepStatus,
        outputs: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        clear_error: bool = False,
    ) -> None:
        """
        Update a specific job step's status and outputs.
        Delegates to JobStepModel for step-specific operations.
        """
        from backend.modules.job.models.job_step_model import JobStepModel
        from datetime import datetime
        
        # Determine timestamps based on status
        started_at = datetime.utcnow() if status == JobStepStatus.PROCESSING else None
        finished_at = datetime.utcnow() if status in [JobStepStatus.COMPLETE, JobStepStatus.FAILED] else None
        
        # Clear error message if requested
        if clear_error:
            error_message = None
            
        JobStepModel.update_step_status(
            job_id=job_id,
            step_id=step_id,
            status=status,
            outputs=outputs,
            started_at=started_at,
            finished_at=finished_at,
            error_message=error_message
        )
