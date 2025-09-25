from datetime import datetime
from shared.modules.job.models.job import Job
from shared.modules.job.models.job_step import JobStep
from pymongo.collection import Collection
from typing import List, Dict, Optional


class JobModel:
    """
    MongoDB persistence wrapper for Job objects.
    """

    def __init__(self, collection: Collection):
        self.collection = collection

    @classmethod
    def create_and_insert(cls, collection: Collection, job_id: str, steps_data: List[Dict]) -> Job:
        """
        Build a Job + JobSteps and insert into Mongo in one step.
        """
        steps = [JobStep(name=s["name"], order=i) for i, s in enumerate(steps_data)]
        job = Job(job_id=job_id, steps=steps, created_at=datetime.utcnow())

        doc = job.dict()
        doc["_id"] = job.job_id
        doc["updated_at"] = datetime.utcnow().isoformat()
        collection.insert_one(doc)

        return job

    def insert(self, job: Job):
        """
        Insert an existing Job instance into Mongo.
        """
        doc = job.dict()
        doc["_id"] = job.job_id
        doc["created_at"] = doc.get("created_at") or datetime.utcnow().isoformat()
        doc["updated_at"] = datetime.utcnow().isoformat()
        self.collection.insert_one(doc)

    def update_job_step(
        self,
        job_id: str,
        step_index: int,
        update_fields: Dict,
        expected_updated_at: Optional[datetime] = None
    ):
        """
        Update a single JobStep in a Job document, optionally using optimistic locking.
        """
        update = {f"steps.{step_index}.{k}": v for k, v in update_fields.items()}
        update["updated_at"] = datetime.utcnow().isoformat()

        query = {"_id": job_id}
        if expected_updated_at:
            query["updated_at"] = expected_updated_at.isoformat()

        res = self.collection.update_one(query, {"$set": update})
        return res.matched_count, res.modified_count
