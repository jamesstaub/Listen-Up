from flask import Flask
from flask_pymongo import PyMongo
import threading
import logging
import os

app = Flask(__name__)

# MongoDB config
app.config["MONGO_URI"] = os.environ.get(
    "MONGO_URI", "mongodb://localhost:27017/listenup-mongo-db"
)
mongo = PyMongo(app)

# Import and register blueprint after mongo is initialized
from backend.api.job_controller import bp as job_controller_bp
app.register_blueprint(job_controller_bp)

from backend.modules.job.backend_queue_service import BackendQueueService

# Global variable to ensure we only start the queue listener once
_queue_listener_started = False

def start_queue_listener():
    """
    Start a background thread that listens for job status updates from Redis.
    """
    global _queue_listener_started
    
    if _queue_listener_started:
        print("🚀 Backend: Queue listener already started, skipping...")
        return
        
    print("🚀 Backend: Starting queue listener thread...")
    _queue_listener_started = True
    
    try:
        service = BackendQueueService(mongo.db)
        print("🎧 Backend: Queue listener service created, starting to run...")
        service.run()
    except Exception as e:
        print(f"❌ Backend: Failed to start queue listener: {e}")
        _queue_listener_started = False  # Reset on error


# Start the queue listener immediately when the module is imported
# This works with both Flask development server and production deployments
print("🌟 Backend: Module loaded, starting background queue listener...")
threading.Thread(target=start_queue_listener, daemon=True).start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=start_queue_listener, daemon=True).start()
    app.run(host="0.0.0.0", port=8000, debug=False)
