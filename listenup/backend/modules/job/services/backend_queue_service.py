from shared.modules.queue.queue_service import QueueService
from shared.modules.queue.redis_client import RedisQueueClient
from shared.modules.job.models.job_step_status_event import JobStepStatusEvent
from backend.factories.service_factory import ServiceFactory
from typing import Dict, Any
import json
import time

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
    
    def __init__(self):
        # Create Redis client for listening to status events FROM microservices
        redis_client = RedisQueueClient(queue_name="job_status_events")
        super().__init__(queue_client=redis_client)
        # Use factory - it will automatically get database from Flask application context
        self.orchestrator = ServiceFactory.create_job_orchestrator()

    def run(self):
        """
        Override the base run method to handle JobStepStatusEvent instead of JobEvent.
        """
        print(f"🎧 {self.__class__.__name__} starting event loop...")
        while True:
            try:
                raw_event = self.queue_client.listen_for_event(timeout=self.poll_timeout)
                if raw_event:
                    print(f"📥 Backend received raw event from queue: {raw_event}")
                    # Don't try to parse as JobEvent - pass raw data directly to handle_event
                    self.handle_event(raw_event)
                else:
                    print("🔍 No events found. Still listening...")
            except Exception as e:
                print(f"❌ An error occurred in the listening loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(10)

    def handle_event(self, event: Any):
        """
        Handle incoming events from the queue.
        Parse JobStepStatusEvent directly without JobEvent validation.
        """
        try:
            print(f"🔥 Backend queue listener received raw event data!")  # Debug log
            print(f"📨 Backend received event: {event}")
            
            # Parse as string if needed
            if isinstance(event, str):
                event = json.loads(event)
            
            # Get the event type from the raw data
            event_type = event.get('event_type')
            print(f"📋 Event type: {event_type}")
            
            if event_type in ['JOB_STEP_COMPLETE', 'JOB_STEP_FAILED', 'JOB_STEP_PROCESSING']:
                print(f"✅ Processing step status event...")
                # This is a status event from a microservice - parse as JobStepStatusEvent
                try:
                    status_event = JobStepStatusEvent(**event)
                    print(f"📊 Parsed status event: job_id={status_event.job_id}, step_id={status_event.step_id}, status={status_event.status}")
                    # Convert the parsed event back to dict for orchestrator
                    status_event_dict = status_event.dict()
                    self.orchestrator.handle_step_status_event(status_event_dict)
                    print(f"✅ Status event handled successfully")
                except Exception as parse_error:
                    print(f"❌ Failed to parse JobStepStatusEvent: {parse_error}")
                    print(f"🔍 Raw event data: {event}")
            else:
                print(f"⚠️  Unknown event type: {event_type}")
                
        except Exception as e:
            print(f"❌ Error handling queue event: {str(e)}")
            print(f"🔍 Exception details: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            
    def start_listening(self):
        """
        Start the queue listening loop.
        """
        print("🎧 BackendQueueService starting to listen for job status events...")
        self.run()  # This calls the parent QueueService.run() method
