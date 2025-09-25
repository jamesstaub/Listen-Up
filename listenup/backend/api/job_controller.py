from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import uuid

from shared.modules.job.models.job import Job
from shared.modules.job.models.job_step import JobStep
from shared.modules.job.job_event_factory import JobEventFactory
from shared.modules.queue.redis_client import RedisQueueClient
from backend.modules.job.models.job_model import JobModel


bp = Blueprint("job_controller", __name__)

redis_client = RedisQueueClient(queue_name="job_events")


@bp.route("/jobs", methods=["POST"])
def create_job():
    """
    Create a new job and enqueue it for processing.
    """
    try:
        payload = request.get_json(force=True)

        steps_data = payload.get("steps")
        if not steps_data or not isinstance(steps_data, list):
            return jsonify({"error": "Invalid or missing 'steps' field"}), 400

        job_id = str(uuid.uuid4())
        created_at = datetime.utcnow()

        # Build Job and JobSteps
        steps = [JobStep(name=step["name"]) for step in steps_data]
        job = Job(job_id=job_id, steps=steps, created_at=created_at)

        # Persist to Mongo
        from flask_pymongo import PyMongo
        mongo = PyMongo(current_app)
        
        job = JobModel.create_and_insert(
            collection=mongo.db.jobs,
            job_id=job_id,
            steps_data=steps_data
        )

        event = JobEventFactory.from_new_job(job)

        redis_client.push_event(event.dict())

        return jsonify(
            {
                "status": "submitted",
                "job_id": job_id,
                "steps": [step.name for step in steps],
            }
        ), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    """
    Fetch job details from MongoDB.
    """
    from flask_pymongo import PyMongo
    mongo = PyMongo(current_app)

    job_doc = mongo.db.jobs.find_one({"_id": job_id})
    if not job_doc:
        return jsonify({"error": "Job not found"}), 404

    job_doc["_id"] = str(job_doc["_id"])
    if "created_at" in job_doc:
        job_doc["created_at"] = job_doc["created_at"].isoformat()

    return jsonify(job_doc), 200
