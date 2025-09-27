from shared.modules.queue.queue_service import QueueService
from shared.modules.queue.redis_client import RedisQueueClient
from shared.modules.job.events import JobEvent
from backend.modules.job.job_orchestrator_service import JobOrchestratorService
from typing import Dict, Any

"""
Backend Queue Service is responsible for:
1. Listening for job status events from microservices
2. Delegating business logic to JobOrchestratorService

This service should be thin and only handle queue interactions.
The actual job orchestration logic is handled by JobOrchestratorService.
"""


class BackendQueueService(QueueService):
    """
    Simplified queue service that only handles queue operations.
    All business logic is delegated to JobOrchestratorService.
    """
    
    def __init__(self, mongo_db):
        # Create Redis client for listening to status events FROM microservices
        redis_client = RedisQueueClient(queue_name="job_status_events")
        super().__init__(queue_client=redis_client)
        self.orchestrator = JobOrchestratorService(mongo_db)

    def handle_event(self, event: JobEvent):
        """
        Handle incoming events from the queue.
        Delegate all business logic to the orchestrator.
        """
        try:
            event_data = event.dict() if hasattr(event, 'dict') else event.__dict__
            print(f"📨 Backend received event: {event_data.get('event_type', 'unknown')}")
            
            # Delegate to orchestrator based on event type
            event_type = event_data.get('event_type')
            
            if event_type in ['JOB_STEP_COMPLETE', 'JOB_STEP_FAILED']:
                # This is a status event from a microservice
                self.orchestrator.handle_step_status_event(event_data)
            else:
                print(f"⚠️  Unknown event type: {event_type}")
                
        except Exception as e:
            print(f"❌ Error handling queue event: {str(e)}")
            
    def start_listening(self):
        """
        Start the queue listening loop.
        """
        print("🎧 BackendQueueService starting to listen for job status events...")
        self.run()  # This calls the parent QueueService.run() method
