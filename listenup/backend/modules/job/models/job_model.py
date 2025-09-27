from datetime import datetime
from typing import List, Dict, Optional, Any

from pymongo.collection import Collection
from shared.modules.job.models.job import Job
from shared.modules.job.models.job_step import JobStep
from shared.modules.job.enums.job_status_enum import JobStatus
from shared.modules.job.enums.job_step_state_enum import JobStepState


class JobModel:
    """
    MongoDB persistence wrapper for Job objects.
    """

    def __init__(self, mongo_db):
        self.db = mongo_db
        self.collection: Collection = mongo_db.jobs

    # ----------------------------
    # Creation / Insertion
    # ----------------------------
    def create_job(self, job: Job) -> Job:
        """
        Insert a new Job into MongoDB.
        """
        doc = job.dict()
        doc["_id"] = job.job_id
        doc["updated_at"] = datetime.utcnow()

        self.collection.insert_one(doc)
        return job

    @classmethod
    def create_and_insert(cls, collection: Collection, job_id: str, steps_data: List[Dict]) -> Job:
        """
        Convenience helper: build a Job from steps + insert it in one go.
        """
        steps = [JobStep(name=s["name"], order=i) for i, s in enumerate(steps_data)]
        job = Job(job_id=job_id, steps=steps, created_at=datetime.utcnow())

        doc = job.dict()
        doc["_id"] = job.job_id
        doc["updated_at"] = datetime.utcnow()

        collection.insert_one(doc)
        return job

    def insert(self, job: Job) -> None:
        """
        Insert an existing Job into MongoDB.
        """
        doc = job.dict()
        doc["_id"] = job.job_id
        doc.setdefault("created_at", datetime.utcnow())
        doc["updated_at"] = datetime.utcnow()

        self.collection.insert_one(doc)

    # ----------------------------
    # Retrieval
    # ----------------------------
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a job by ID.
        """
        job_doc = self.collection.find_one({"_id": job_id})
        if job_doc:
            job_doc["job_id"] = str(job_doc["_id"])
        return job_doc

    # ----------------------------
    # Updates
    # ----------------------------
    def update_job_status(self, job_id: str, status: JobStatus) -> None:
        """
        Update the overall job status.
        """
        self.collection.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": status.value if hasattr(status, "value") else str(status),
                    "updated_at": datetime.utcnow(),
                }
            },
        )

    def update_job_step_status(
        self,
        job_id: str,
        step_id: str,
        status: JobStepState,
        outputs: Optional[List[str]] = None,
        error_message: Optional[str] = None,
        clear_error: bool = False,
    ) -> None:
        """
        Update a specific job step's status and outputs.
        """
        update_fields: Dict[str, Any] = {
            "steps.$.status": status.value if hasattr(status, "value") else str(status),
            "updated_at": datetime.utcnow(),
        }

        if outputs is not None:
            update_fields["steps.$.outputs"] = outputs

        if error_message is not None:
            update_fields["steps.$.error_message"] = error_message
        elif clear_error:
            update_fields["steps.$.error_message"] = None

        self.collection.update_one(
            {"_id": job_id, "steps.step_id": step_id},
            {"$set": update_fields},
        )

    def update_job_step(
        self,
        job_id: str,
        step_index: int,
        update_fields: Dict[str, Any],
        expected_updated_at: Optional[datetime] = None,
    ):
        """
        Update a single JobStep in a Job document, optionally using optimistic locking.
        """
        update = {f"steps.{step_index}.{k}": v for k, v in update_fields.items()}
        update["updated_at"] = datetime.utcnow()

        query: Dict[str, Any] = {"_id": job_id}
        if expected_updated_at:
            query["updated_at"] = expected_updated_at

        res = self.collection.update_one(query, {"$set": update})
        return res.matched_count, res.modified_count
