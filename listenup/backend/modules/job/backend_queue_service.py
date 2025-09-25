from shared.modules.job.enums.job_step_state_enum import JobStepState
from pymongo.errors import PyMongoError
from shared.modules.job.events import JobEvent
from shared.modules.queue.queue_service import QueueService
from ..job.models.job_step_model import JobStepModel

class BackendQueueService(QueueService):
    def __init__(self, db, mongo_client):
        self.db = db
        self.mongo_client = mongo_client

    def handle_event(self, event: dict):
        job_event = JobEvent(**event)
        job_id = job_event.job_id

        MAX_RETRIES = 5
        retries = 0

        while retries < MAX_RETRIES:
            with self.mongo_client.start_session() as session:
                try:
                    session.start_transaction()
                    self._update_job_status_in_mongo(session, job_id, job_event)
                    session.commit_transaction()
                    break
                except PyMongoError:
                    session.abort_transaction()
                    retries += 1

    def _update_job_status_in_mongo(self, session, job_id, job_event: JobEvent):
        jobs_collection = self.db.jobs

        if "step_id" in job_event.payload:
            step_id = job_event.payload["step_id"]
            step_status = job_event.payload.get("step_state")
            update_fields = {"outputs": job_event.payload.get("step_outputs", {})}

            if isinstance(step_status, str):
                step_status = JobStepState(step_status)

            if step_status is not None and isinstance(step_status, JobStepState):
                JobStepModel(jobs_collection).update_status(
                    job_id=job_id,
                    step_id=step_id,
                    status=step_status,
                    updates=update_fields
                )
            else:
                # TODO: Log invalid step_status error
                pass
        else:
            update_doc = {
                "$set": {"status": job_event.status},
                "$push": {"logs": job_event.dict()},
            }
            jobs_collection.find_one_and_update({"_id": job_id}, update_doc, session=session)
