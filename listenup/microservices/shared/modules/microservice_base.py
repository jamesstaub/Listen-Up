import os
import logging
from abc import ABC, abstractmethod
from microservices_shared.modules.queue.microservice_queue_service import (
    MicroserviceQueueService,
)
from shared.modules.assets.asset_manager_factory import create_asset_manager
from shared.modules.job.job_event_factory import JobEventFactory
from microservices_shared.modules.job.machines.step_state_machine import (
    StepStateMachine,
)


class MicroserviceBase(ABC):
    """
    Base class for microservices. Manages job processing via StepStateMachine
    and publishes status/events to the queue.
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.INFO)
        self.asset_manager = create_asset_manager()

        self.redis_host = os.environ.get("REDIS_HOST", "localhost")
        self.redis_port = int(os.environ.get("REDIS_PORT", 6379))

    @abstractmethod
    def get_manifest(self):
        """Return the manifest instance for this microservice."""
        pass

    @abstractmethod
    def get_queue_service_class(self):
        """Return the QueueService subclass for this microservice."""
        return MicroserviceQueueService

    def _get_redis_client(self):
        """Instantiate Redis client for job events."""
        from shared.modules.queue.redis_client import RedisQueueClient

        return RedisQueueClient(
            host=self.redis_host, port=self.redis_port, queue_name="job_events"
        )

    def run(self):
        """
        Main event loop: fetch jobs from queue, run each step via StepStateMachine,
        and publish structured events.
        """
        self.logger.info(f"{self.service_name} starting microservice loop...")
        redis_client = self._get_redis_client()
        manifest = self.get_manifest()
        queue_service_cls = self.get_queue_service_class()
        queue_service = queue_service_cls(redis_client=redis_client, manifest=manifest)

        queue_service.run()  # QueueService.run will call handle_event for each job

    # --- Event publishing helpers ---
    def _publish_status_update(self, job):
        """Publish overall job status update."""
        self._publish(JobEventFactory.from_job_status(job))

    def _publish_progress_update(self, job_id, message, percentage=None):
        """Publish progress message for in-progress steps."""
        self._publish(JobEventFactory.from_progress(job_id, message, percentage))

    def _publish_log_message(self, job_id, message, level="INFO"):
        """Publish log message from a step."""
        self._publish(JobEventFactory.from_log(job_id, message, level))

    def _publish_final_status(self, job):
        """Publish job final status."""
        self._publish(JobEventFactory.from_job_final(job))

    def _publish(self, event):
        """Push event to Redis queue."""
        client = self._get_redis_client()
        client.push_event(event.dict())
        self.logger.debug(f"Published event: {event.dict()}")
