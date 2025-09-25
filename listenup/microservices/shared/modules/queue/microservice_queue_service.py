from typing import Any, Dict
from shared.modules.job.models.job import Job
from shared.modules.job.job_event_factory import JobEventFactory
from shared.modules.queue.queue_service import QueueService
from microservices_shared.modules.job.machines.step_state_machine import StepStateMachine


class MicroserviceQueueService(QueueService):
    """
    Listens for job events from Redis and executes them using StepStateMachine.
    Publishes status updates to the queue via JobEventFactory.
    """

    def __init__(self, redis_client: Any, manifest: Any):
        self.redis_client = redis_client
        self.manifest = manifest
        super().__init__(queue_handler=redis_client)
        print("MicroserviceQueueService initialized and ready to start listening.")

    def handle_event(self, event: Dict[str, Any]):
        """
        Called automatically by QueueService.run() whenever a new job event arrives.
        """
        job_data = event.get("data")
        if not job_data:
            return
            
        job = Job.parse_obj(job_data)
        job_id = job.job_id

        # --- Start the job ---
        self._publish(JobEventFactory.from_job_status(job_id, "processing"))

        # --- Process each step ---
        for step_index, step in enumerate(job.steps):
            if step_index < job.current_step_index:
                continue  # Skip already processed steps
                
            # Wrap step in its state machine
            step_machine = StepStateMachine(step)
            step_machine.execute(manifest=self.manifest, asset_manager=None)  # provide asset_manager if needed

            # Publish step update
            self._publish(JobEventFactory.from_step_update(job, step))

            # If step failed, fail the job
            if step.state == "failed":
                self._publish(JobEventFactory.from_job_status(job_id, "failed"))
                return

        # --- Finish job if not failed ---
        self._publish(JobEventFactory.from_job_status(job_id, "complete"))

    def _publish(self, event):
        """Serialize and push an event to Redis."""
        self.redis_client.push_event(event.dict())
