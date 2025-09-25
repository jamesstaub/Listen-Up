from flask import Flask
from flask_pymongo import PyMongo
import threading
import logging
import os

from backend.api.job_controller import bp as job_controller_bp
from backend.modules.job.backend_queue_service import BackendQueueService

app = Flask(__name__)
app.register_blueprint(job_controller_bp)

# MongoDB config
app.config["MONGO_URI"] = os.environ.get(
    "MONGO_URI", "mongodb://localhost:27017/jobsdb"
)
mongo = PyMongo(app)


def start_queue_listener():
    """
    Start a background thread that listens for job status updates from Redis.
    """
    from shared.modules.queue.redis_client import RedisQueueClient

    queue_handler = RedisQueueClient(queue_name="job_status_updates")
    service = BackendQueueService(
        db=mongo.db,
        mongo_client=mongo.cx,
    )
    service.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=start_queue_listener, daemon=True).start()
    app.run(host="0.0.0.0", port=8000, debug=False)
